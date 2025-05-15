from crewai import Agent, Task, Crew
# Removed: from langchain_openai import ChatOpenAI
import json
from openai import AzureOpenAI
import os

# Load the cold data (last close prices)
with open(r'D:\version1.0.0\Yahoo\Outputs\2025-05-09_stock_last_close.json') as f:
    last_close_data = json.load(f)

# 1. CAG Injection Agent
cag_agent = Agent(
    role='Stock Data Injector',
    goal='Inject last close prices into the analysis context',
    backstory='Specialized in providing cold data context for stock analysis',
    verbose=True,
    allow_delegation=False,
    llm=ChatOpenAI(model="gpt-4o")
)

# 2. Per-Symbol Analysis Agent
# Initialize Azure OpenAI client (add this near the top)
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),  
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Update the analysis agent configuration
analysis_agent = Agent(
    role='Stock Analyst',
    goal='Perform detailed analysis per stock symbol using transcript insights',
    backstory='Expert in technical and fundamental analysis of stocks',
    verbose=True,
    allow_delegation=False,
    llm=None,  # We'll handle the LLM call manually
    tools=[],  # No tools needed since we're doing custom API calls
    function=lambda prompt: (
        client.chat.completions.create(
            model="gpt-4o-mini",  # Or your deployment name
            messages=[
                {
                    "role": "system", 
                    "content": "You are a financial analyst expert who specializes in extracting technical analysis from transcripts. Your response must be a valid JSON object."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            response_format={"type": "json_object"}
        ).choices[0].message.content
    )
)

# Update the analyze_transcript function
def analyze_transcript(transcript_path):
    with open(transcript_path, 'r') as f:
        transcript = f.read()
    
    # Create prompt with last close data context
    prompt = f"""
    Analyze this YouTube transcript for stock insights:
    {transcript}
    
    Last close prices reference:
    {json.dumps(last_close_data, indent=2)}
    
    Return analysis including support/resistance levels, trends, and recommendations in JSON format.
    """
    
    analysis_task = Task(
        description=prompt,
        agent=analysis_agent,
        expected_output="JSON analysis per stock symbol",
        context=[cag_task]
    )
    
    crew = Crew(
        agents=[cag_agent, analysis_agent, validation_agent],
        tasks=[cag_task, analysis_task, validation_task],
        verbose=2
    )
    
    return crew.kickoff()

validation_task = Task(
    description="Validate analysis outputs ensuring support < last close, resistance > last close etc.",
    agent=validation_agent,
    expected_output="Validated analysis with technical confirmation",
    context=[analysis_task]
)

# Create and run crew
crew = Crew(
    agents=[cag_agent, analysis_agent, validation_agent],
    tasks=[cag_task, analysis_task, validation_task],
    verbose=2
)

def main():
    # Test with sample transcript
    result = analyze_transcript(r'D:\version1.0.0\Yahoo\Outputs\sample.txt')
    
    # Save results to file
    with open(r'D:\version1.0.0\Yahoo\Outputs\2025-05-09_stock_last_close.json', 'w') as f:
        json.dump(json.loads(result), f, indent=2)
    
    print("Analysis saved to d:\\test\\analysis_results.json")

if __name__ == "__main__":
    main()