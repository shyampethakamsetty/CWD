from crewai import Agent, Task, Crew
import os
import json
import glob
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging
from Yahoo.Tools.context_agent import ContextAgent
from openai import OpenAI

# Configure logging
logging.basicConfig(
    filename='transcript_analysis.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ContextIngestionAgent:
    def __init__(self):
        self.agent = Agent(
            role='Stock Context Provider',
            goal='Provide accurate stock price context for analysis',
            backstory="""You are a financial data expert who maintains and provides 
            up-to-date stock price context for analysis. You ensure the data is fresh 
            and relevant for meaningful analysis.""",
            verbose=True,
            allow_delegation=False
        )
        self._context = None
        self._context_date = None
        self.cag = ContextAgent()
    
    def get_context(self) -> str:
        today = datetime.now().date()
        if self._context_date == today and self._context:
            return self._context
        self._context = self.cag.prepare_context()
        self._context_date = today
        return self._context

class TranscriptAnalyzerAgent:
    def __init__(self):
        self.agent = Agent(
            role='Financial Transcript Analyzer',
            goal='Extract valuable insights from financial transcripts',
            backstory="""You are an expert financial analyst specialized in 
            analyzing transcripts to extract market insights, technical levels, 
            and sentiment. You consider both the transcript content and current 
            market context.""",
            verbose=True,
            allow_delegation=True
        )
        self.client = OpenAI()
    
    def analyze(self, transcript: str, context: str) -> Dict:
        analysis_prompt = f"""
        Using the following stock price context:
        {context}
        
        Please analyze this transcript for financial insights:
        {transcript}
        
        Provide detailed analysis including:
        1. Key price levels mentioned
        2. Market sentiment
        3. Technical analysis points
        4. Notable stock mentions and context
        
        Format the response as a JSON object with the following structure:
        {{
            "key_price_levels": [
                {{"symbol": "TICKER", "support": 00.00, "resistance": 00.00}}
            ],
            "market_sentiment": "bullish/bearish/neutral",
            "technical_analysis": [
                {{"point": "description"}}
            ],
            "stock_mentions": [
                {{"symbol": "TICKER", "context": "discussion_summary"}}
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial analyst expert who analyzes transcripts and provides structured insights."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Error in LLM analysis: {str(e)}")
            return {
                "error": str(e),
                "key_price_levels": [],
                "market_sentiment": "unknown",
                "technical_analysis": [],
                "stock_mentions": []
            }

class ValidatorAgent:
    def __init__(self):
        self.agent = Agent(
            role='Analysis Validator',
            goal='Ensure analysis accuracy and consistency',
            backstory="""You are a meticulous financial validator who ensures 
            all analysis outputs are accurate, consistent, and properly formatted. 
            You check for technical accuracy and data consistency.""",
            verbose=True,
            allow_delegation=False
        )
        self.client = OpenAI()
    
    def validate(self, analysis: Dict, context: str) -> Dict:
        validation_prompt = f"""
        Given the following analysis and market context:

        Analysis:
        {json.dumps(analysis, indent=2)}

        Market Context:
        {context}

        Please validate and ensure:
        1. Support levels are below current price
        2. Resistance levels are above current price
        3. Technical analysis points are consistent with price levels
        4. Stock mentions match discussed symbols
        5. Sentiment is properly justified

        If any issues are found, correct them and return the fixed analysis.
        If no issues are found, return the original analysis.
        
        Return the response in the same JSON format as the input.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial validation expert who ensures analysis accuracy and consistency."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.3  # Lower temperature for more consistent validation
            )
            
            validated_analysis = json.loads(response.choices[0].message.content)
            logging.info("Validation completed successfully")
            return validated_analysis
            
        except Exception as e:
            logging.error(f"Error in validation: {str(e)}")
            return analysis  # Return original analysis if validation fails

class CentralBrainAgent:
    def __init__(self):
        self.agent = Agent(
            role='Analysis Coordinator',
            goal='Orchestrate and optimize the analysis pipeline',
            backstory="""You are an intelligent coordinator that optimizes the analysis 
            workflow. You understand when to refresh context, how to prioritize analysis, 
            and can make decisions about the analysis process.""",
            verbose=True,
            allow_delegation=True,
            tools=[
                self.check_context_freshness,
                self.prioritize_transcripts,
                self.evaluate_analysis_quality
            ]
        )
        self.context_agent = ContextIngestionAgent()
        self.analyzer_agent = TranscriptAnalyzerAgent()
        self.validator_agent = ValidatorAgent()
        self.client = OpenAI()

    def check_context_freshness(self, context: str) -> bool:
        """Tool to check if the context needs refreshing"""
        prompt = f"""
        Given this market context data:
        {context}
        
        Determine if this context is still relevant and fresh enough for analysis.
        Consider:
        1. Time since last update
        2. Any major market events that might have occurred
        3. Significance of price changes
        
        Return only "true" if fresh enough, "false" if needs update.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a market data freshness evaluator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip().lower() == "true"

    def prioritize_transcripts(self, transcripts: List[Dict]) -> List[Dict]:
        """Tool to prioritize which transcripts to analyze first"""
        prompt = f"""
        Given these transcripts:
        {json.dumps(transcripts, indent=2)}
        
        Prioritize them based on:
        1. Relevance to current market conditions
        2. Expected impact on market
        3. Company market cap and trading volume
        4. Timing of release
        
        Return the list of transcript IDs in priority order.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial prioritization expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return json.loads(response.choices[0].message.content)

    def evaluate_analysis_quality(self, analysis: Dict) -> Dict:
        """Tool to evaluate the quality and completeness of analysis"""
        prompt = f"""
        Evaluate this analysis for quality and completeness:
        {json.dumps(analysis, indent=2)}
        
        Check for:
        1. Depth of insights
        2. Clarity of price levels
        3. Sentiment justification
        4. Technical analysis thoroughness
        5. Missing important elements
        
        Return a quality score (0-100) and improvement suggestions.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial analysis quality expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return json.loads(response.choices[0].message.content)

    def create_tasks(self, transcript_files: List[Path]) -> List[Task]:
        # Read transcripts first for prioritization
        transcripts = []
        for file in transcript_files:
            with open(file, 'r') as f:
                transcripts.append({
                    "id": file.stem,
                    "content": json.load(f)
                })

        # Context evaluation task
        context_evaluation_task = Task(
            description="""Evaluate current market context freshness and relevance. 
            Decide if we need to refresh the context data.""",
            agent=self.agent,
            expected_output="Context freshness evaluation",
        )

        # Context retrieval task
        context_task = Task(
            description="""Retrieve and validate current stock price context. 
            Ensure it's fresh and relevant for today's analysis.""",
            agent=self.context_agent.agent,
            expected_output="Fresh stock price context data",
            context=[context_evaluation_task]
        )

        # Prioritization task
        prioritization_task = Task(
            description="""Analyze all available transcripts and prioritize them 
            based on market impact and relevance.""",
            agent=self.agent,
            expected_output="Prioritized list of transcripts",
            context=[context_task]
        )

        tasks = [context_evaluation_task, context_task, prioritization_task]
        
        # Create analysis tasks based on priority
        for transcript in transcripts:
            analysis_task = Task(
                description=f"""Analyze transcript {transcript['id']} using current 
                market context. Extract key insights, price levels, and sentiment.""",
                agent=self.analyzer_agent.agent,
                expected_output="Structured analysis in JSON format",
                context=[context_task]
            )
            
            quality_task = Task(
                description="""Evaluate the quality and completeness of the analysis. 
                Identify any gaps or areas needing improvement.""",
                agent=self.agent,
                expected_output="Analysis quality evaluation",
                context=[analysis_task]
            )
            
            validation_task = Task(
                description="""Validate and improve analysis results based on quality evaluation. 
                Ensure all insights are accurate and valuable.""",
                agent=self.validator_agent.agent,
                expected_output="Validated and improved analysis",
                context=[analysis_task, quality_task]
            )
            
            tasks.extend([analysis_task, quality_task, validation_task])
        
        return tasks

    def process_transcripts(self):
        # Get latest transcripts folder
        base_path = Path("OUTPUTS")
        date_folders = [d for d in base_path.iterdir() if d.is_dir()]
        latest_folder = max(date_folders, key=lambda x: x.name)
        transcripts_folder = latest_folder / "transcripts"
        
        if not transcripts_folder.exists():
            raise FileNotFoundError(f"No transcripts folder found in {latest_folder}")
        
        # Get transcript files
        transcript_files = list(transcripts_folder.glob("*.json"))
        
        # Create tasks
        tasks = self.create_tasks(transcript_files)
        
        # Create crew
        crew = Crew(
            agents=[
                self.context_agent.agent,
                self.analyzer_agent.agent,
                self.validator_agent.agent,
                self.agent  # Central brain agent
            ],
            tasks=tasks,
            verbose=2
        )
        
        # Execute analysis pipeline
        results = crew.kickoff()
        
        # Save results
        analysis_folder = transcripts_folder.parent / "analysis"
        analysis_folder.mkdir(exist_ok=True)
        
        for transcript_file, result in zip(transcript_files, results[1::2]):  # Skip context results
            analysis_file = analysis_folder / f"{transcript_file.stem}_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            logging.info(f"Successfully analyzed and validated {transcript_file.name}")

def main():
    brain = CentralBrainAgent()
    brain.process_transcripts()

if __name__ == "__main__":
    main()