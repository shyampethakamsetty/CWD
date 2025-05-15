from crewai import Agent
import os
import json
import logging
from dotenv import load_dotenv
from openai import AzureOpenAI
import glob
from datetime import datetime

# Initialize logging with a better format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('transcript_analysis.log')
    ]
)

# Load environment variables from .env file
load_dotenv()

# Configure Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Get deployment name from environment variables
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

if not deployment_name:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is not set")

# Update the chat completion call
def load_lastclose_data(date_str=None):
    """Load last close prices from Yahoo output JSON file"""
    if date_str is None:
        # Use today's date if no specific date provided
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Find the most recent file matching the pattern
    files = glob.glob(f"Yahoo\\Outputs\\*_stock_last_close.json")
    if not files:
        raise FileNotFoundError("No last close JSON files found in Yahoo\\Outputs")
    
    # Sort files by date and pick the most recent one
    latest_file = sorted(files, reverse=True)[0]
    
    with open(latest_file, 'r') as f:
        return json.load(f)

def analyze_transcript(transcript_text):
    try:
        # Load last close data
        lastclose_data = load_lastclose_data()
        
        # Create enhanced prompt with CAG context
        prompt = f"""
        Analyze ONLY the stocks explicitly mentioned in the transcript. 
        Here are the last close prices for reference:
        {json.dumps(lastclose_data, indent=2)}
        
        For each mentioned stock symbol, extract:
        1. Support levels (with exact price points)
        2. Resistance levels (with exact price points)
        3. Direction (bullish/bearish/neutral)
        4. Key insights from the discussion
        5. Risk factors mentioned
        6. Any price targets or technical levels discussed
        
        Include all numerical values with their context.
        Format response as JSON with symbols as keys.
        
        Transcript:
        {transcript_text}
        """
        
        # Call the Azure OpenAI API with the updated syntax
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are a financial analyst expert who specializes in extracting technical analysis from transcripts. Your response must be a valid JSON object."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        # Simplified logging
        logging.info("API call successful. Processing response.")
        
        try:
            analysis_data = json.loads(response.choices[0].message.content)
            return analysis_data
        except json.JSONDecodeError as je:
            logging.error("Failed to parse JSON response: %s", str(je))
            return {"error": f"Failed to parse JSON response: {str(je)}"}
        
    except Exception as e:
        logging.error("Error during transcript analysis: %s", str(e))
        return {"error": str(e)}

# Define the Validator Agent
class ValidatorAgent:
    def run(self, analysis_data, context):
        """Validate analysis against cold data"""
        lastclose_data = context['lastclose_data']
        errors = []
        
        for symbol, analysis in analysis_data.items():
            if symbol not in lastclose_data:
                continue
                
            last_close = lastclose_data[symbol]
            
            # Validate support levels
            for support in analysis.get('Support Levels', []):
                if support >= last_close:
                    errors.append(f"Invalid support {support} >= last close {last_close} for {symbol}")
            
            # Validate resistance levels
            for resistance in analysis.get('Resistance Levels', []):
                if resistance <= last_close:
                    errors.append(f"Invalid resistance {resistance} <= last close {last_close} for {symbol}")
        
        if errors:
            logging.error("Validation failed:\n" + "\n".join(errors))
            return {"error": "Invalid technical levels", "details": errors}
            
        return analysis_data

def format_analysis_output(analysis_data):
    """
    Format the analysis data into a readable output
    """
    if "error" in analysis_data:
        return f"Analysis Error: {analysis_data['error']}"
    
    # Just store the raw response in a formatted way
    output = json.dumps(analysis_data, indent=2)
    
    return output

# Define the CAG Ingestion Agent
class CAGIngestionAgent:
    def __init__(self):
        self.description = "Ingests and prepares market data for analysis"
        self.verbose = True
        self.memory = True
        self.expected_input = "None (initial data loader)"
        self.expected_output = "Processed market context for analysis"

    def run(self):
        """Load and structure cold data (last close prices)"""
        try:
            lastclose_data = load_lastclose_data()
            logging.info(f"Loaded last close data for {len(lastclose_data)} symbols")
            return {
                "lastclose_data": lastclose_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Failed to load cold data: {str(e)}")
            raise
        logging.info("Preparing market context...")
        return {
            "timestamp": datetime.now().isoformat(),
            "lastclose_data": lastclose_data,
            "market_context": "Current market data from Yahoo Finance",
            "deployment_name": deployment_name
        }

class AnalyzerAgent:
    def __init__(self):
        self.description = "Analyzes transcripts for technical insights"
        self.verbose = True
        self.tools = []
        self.expected_input = "Transcript text and market context"
        self.expected_output = "Technical analysis with support/resistance levels"

    def run(self, transcript_text, context):
        """Analyze transcript with reference to cold data"""
        lastclose_data = context['lastclose_data']
        
        prompt = f"""
        Analyze this trading transcript with reference to these last close prices:
        {json.dumps(lastclose_data, indent=2)}
        
        For each mentioned stock, provide:
        - Support levels (must be BELOW last close)
        - Resistance levels (must be ABOVE last close) 
        - Direction (bullish/bearish/neutral)
        - Key insights
        - Risk factors
        - Price targets
        
        Rules:
        1. Support levels MUST be below last close price
        2. Resistance levels MUST be above last close price
        3. Only include levels explicitly mentioned
        4. Never invent numbers not in transcript
        
        Transcript:
        {transcript_text}
        """
        
        # Call the Azure OpenAI API
        response = client.chat.completions.create(
            model=context['deployment_name'],
            messages=[
                {"role": "system", "content": "You are a financial analyst expert who specializes in extracting technical analysis from transcripts. Your response must be a valid JSON object."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            response_format={"type": "json_object"}
        )
        
        logging.debug(f"Raw API response received for analysis")
        return json.loads(response.choices[0].message.content)

class ValidatorAgent:
    def __init__(self):
        self.description = "Validates analysis results"
        self.verbose = True
        self.expected_input = "Analysis data and last close prices"
        self.expected_output = "Validated analysis or error"

    def run(self, analysis_data, lastclose_data):
        logging.info("Validating analysis results...")
        required_keys = ['support_levels', 'resistance_levels', 'direction']
        
        for symbol, data in analysis_data.items():
            # Check required structure
            for key in required_keys:
                if key not in data:
                    logging.error(f"Missing required key '{key}' for {symbol}")
                    return {"error": f"Invalid analysis format for {symbol}"}
            
            # Only validate support if provided
            if 'support_levels' in data and data['support_levels']:
                for level in data['support_levels']:
                    if level >= lastclose_data.get(symbol, float('inf')):
                        logging.warning(f"Support level {level} >= last close for {symbol}")
                        return {"error": f"Invalid support level for {symbol}"}
                        
        logging.info("Validation completed successfully")
        return analysis_data

class CrewAI:
    def __init__(self, agents):
        self.agents = {agent.__class__.__name__: agent for agent in agents}
        self.tasks = []
        logging.info(f"Initialized CrewAI with {len(self.agents)} specialized agents")

    def add_task(self, agent_name, expected_output):
        self.tasks.append({
            'agent': agent_name,
            'expected_output': expected_output
        })

    def run_agent(self, agent_name, *args, **kwargs):
        logging.info(f"Executing {agent_name}...")
        agent = self.agents.get(agent_name)
        if not agent:
            logging.error(f"Agent {agent_name} not found")
            raise ValueError(f"Agent {agent_name} not found")
        
        try:
            result = agent.run(*args, **kwargs)
            logging.info(f"{agent_name} completed successfully")
            return result
        except Exception as e:
            logging.error(f"{agent_name} failed: {str(e)}")
            raise

def get_latest_output_folder():
    """Get the most recent output folder in OUTPUTS directory"""
    output_folders = glob.glob("OUTPUTS\\*")
    if not output_folders:
        raise FileNotFoundError("No output folders found in OUTPUTS directory")
    return max(output_folders, key=os.path.getmtime)

def process_transcripts():
    """Process all transcripts in the latest output folder"""
    latest_folder = get_latest_output_folder()
    transcripts_path = os.path.join(latest_folder, "transcripts")
    
    if not os.path.exists(transcripts_path):
        raise FileNotFoundError(f"No transcripts folder found in {latest_folder}")
    
    transcript_files = glob.glob(os.path.join(transcripts_path, "*.json"))
    
    for transcript_file in transcript_files:
        try:
            with open(transcript_file, 'r') as f:
                transcript_data = json.load(f)
            
            analysis = analyze_transcript(transcript_data['transcript'])
            
            # Save analysis to same folder structure
            analysis_filename = os.path.basename(transcript_file).replace('.json', '_analysis.json')
            analysis_path = os.path.join(latest_folder, "analysis", analysis_filename)
            
            os.makedirs(os.path.dirname(analysis_path), exist_ok=True)
            
            with open(analysis_path, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            logging.info(f"Processed {os.path.basename(transcript_file)} successfully")
            
        except Exception as e:
            logging.error(f"Error processing {transcript_file}: {str(e)}")

def main():
    # Initialize agents
    crew = CrewAI(agents=[
        CAGIngestionAgent(),
        AnalyzerAgent(), 
        ValidatorAgent()
    ])
    
    # Load cold data
    context = crew.run_agent('CAGIngestionAgent')
    
    # Process transcript
    with open(r'OUTPUTS\2025-05-10\transcripts\Lth5lVjFK8U.json') as f:
        transcript_data = json.load(f)
    
    analysis = crew.run_agent('AnalyzerAgent', transcript_data['transcript'], context)
    validated = crew.run_agent('ValidatorAgent', analysis, context)
    
    # Save results
    with open(r'OUTPUTS\2025-05-10\transcripts\Lth5lVjFK8U_analysis.json', 'w') as f:
        json.dump(validated, f, indent=2)
    
    # Process all transcripts
    process_transcripts()
    
    logging.info("Transcript analysis pipeline completed")

if __name__ == "__main__":
    main()