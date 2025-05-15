from crewai import Task, Crew
from context_agent import ContextAgent
from typing import Dict, Any, Optional
import logging
import os
import sys
from datetime import datetime
import json
from pathlib import Path

# Configure logging with more detailed formatting
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure logs directory exists
log_dir = os.path.join('Yahoo', 'Logs')
os.makedirs(log_dir, exist_ok=True)

# File handler with current date
log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y-%m-%d")}_workflow.log')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class StockDataWorkflow:
        def __init__(self, config: Optional[Dict[str, Any]] = None):
                """Initialize the workflow manager."""
                self.current_date = datetime.now().strftime("%Y-%m-%d")
                self.output_dir = os.path.join('Yahoo', 'Outputs')
                os.makedirs(self.output_dir, exist_ok=True)
                
                # Initialize configuration
                self.config = config or {}
                
                # Initialize state
                self.state = {
                    'current_date': self.current_date,
                    'output_file': os.path.join(self.output_dir, f'{self.current_date}_stock_last_close.json'),
                    'status': 'initialized',
                    'last_run': None,
                    'last_data': None,
                    'error': None,                'config': self.config
                }
                
                # Load previous run data
                self.state['last_data'] = self._load_last_run_data()
                logger.info(f"Workflow initialized for date: {self.current_date}")

        def _load_last_run_data(self):
                """Load the last run's data if available."""
                try:
                    output_file = self.state['output_file']
                    if os.path.exists(output_file):
                        with open(output_file, 'r') as f:
                            data = json.load(f)
                        logger.info(f"Loaded previous run data from {output_file}")
                        return data
                except Exception as e:
                    logger.warning(f"Could not load previous run data: {str(e)}")
                    return None
                
        def setup_task(self) -> Task:
                """Create and configure the task for the ContextAgent."""
                logger.info("Setting up stock data collection task")
                
                # Initialize agent with configuration
                context_agent = ContextAgent(config=self.config)
                
                # Get previous run data for context
                last_data = self.state.get('last_data')
                last_run = self.state.get('last_run')
                
                # Create context as a list instead of a string
                context_list = [
                    f"Current date is {self.current_date}",
                    f"Output will be saved to {self.state['output_file']}",
                    f"Previous run date: {last_run if last_run else 'No previous run data'}",
                    f"{'Previous data is available' if last_data else 'No previous data available'}",
                    "Configuration:"
                ]
                
                # Add configuration items to the context list
                for k, v in self.config.items():
                    context_list.append(f"  - {k}: {v}")
                
                # Create task with proper configuration
                task = Task(
                    description="Fetch and maintain stock price data for configured symbols",
                    expected_output="A dictionary containing stock symbols as keys and their latest closing prices as values",
                    agent=context_agent,
                    async_execution=False,
                    context=context_list
                )
                logger.info("Task configured successfully")
                return task

        def create_crew(self, task: Task) -> Crew:
                """Create and configure the CrewAI instance."""
                logger.info("Creating CrewAI instance")
                crew = Crew(
                    agents=[task.agent],
                    tasks=[task],
                    verbose=True
                )
                logger.info("CrewAI instance created with ContextAgent")
                return crew

        def execute(self) -> Dict[str, Any]:
                """
                Execute the stock data collection workflow.
                
                Returns:
                    Dict[str, Any]: Results of the workflow execution
                """
                start_time = datetime.now()
                logger.info(f"Starting workflow execution at {start_time}")
                
                try:
                    # Setup and execute task
                    task = self.setup_task()
                    crew = self.create_crew(task)
                    
                    # Execute the workflow
                    logger.info("Executing stock data collection workflow")
                    results = crew.kickoff()
                    
                    # Validate results
                    if not isinstance(results, dict):
                        raise ValueError("Invalid results format returned from agent")
                        
                    if not results.get('data'):
                        raise ValueError("No stock data returned from agent")
                    
                    # Calculate statistics
                    previous_data = self.state.get('last_data', {})
                    changes = {
                        'new': len(set(results['data'].keys()) - set(previous_data.keys())),
                        'updated': len([k for k in results['data'] if k in previous_data 
                                     and results['data'][k] != previous_data[k]]),
                        'unchanged': len([k for k in results['data'] if k in previous_data 
                                       and results['data'][k] == previous_data[k]]),
                        'missing': len(set(previous_data.keys()) - set(results['data'].keys()))
                    }
                    
                    # Update state
                    end_time = datetime.now()
                    execution_time = end_time - start_time
                    
                    self.state.update({
                        'status': 'completed',
                        'last_run': end_time.isoformat(),
                        'execution_time': str(execution_time),
                        'symbols_processed': len(results['data']),
                        'last_data': results['data'],
                        'changes': changes,
                        'error': None
                    })
                    
                    # Log completion details
                    logger.info(f"Workflow completed in {execution_time}")
                    logger.info(f"Processed {self.state['symbols_processed']} symbols")
                    logger.info("Changes summary:")
                    for change_type, count in changes.items():
                        logger.info(f"  {change_type}: {count}")
                    logger.info(f"Results saved to: {self.state['output_file']}")
                    
                    return results
                    
                except Exception as e:
                    self.state['status'] = 'failed'
                    self.state['error'] = str(e)
                    logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
                    raise

        def get_state(self) -> Dict[str, Any]:
                """Get the current state of the workflow."""
                return self.state

def main():
    """Main entry point for the workflow."""
    try:
        logger.info("Initializing stock data workflow")
        
        # Default configuration
        config = {
            'RETRY_ATTEMPTS': 3,
            'RETRY_DELAY': 5,
            'RATE_LIMIT_DELAY': 1,
            'BATCH_SIZE': 50
        }
        
        # Initialize and execute workflow
        workflow = StockDataWorkflow(config=config)
        results = workflow.execute()
        
        # Validate results
        if results and isinstance(results.get('data'), dict):
            # Get final state and changes
            state = workflow.get_state()
            changes = state.get('changes', {})
            
            # Log final state with improved formatting
            logger.info("\nWorkflow Summary:")
            logger.info("-----------------")
            logger.info(f"Status: {state['status']}")
            logger.info(f"Execution Time: {state['execution_time']}")
            logger.info(f"Symbols Processed: {state['symbols_processed']}")
            logger.info("\nChanges:")
            for change_type, count in changes.items():
                logger.info(f"  {change_type.capitalize()}: {count}")
            logger.info(f"\nOutput File: {state['output_file']}")
            
            return results
        else:
            logger.error("Invalid results format returned from workflow")
            return None
        
    except Exception as e:
        logger.error(f"Critical error in workflow: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Workflow process completed")

if __name__ == "__main__":
    main()
