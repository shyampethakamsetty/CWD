import streamlit as st
from stock_analyzer import analyze_stock_query

def main():
    st.title("Stock Analysis Chat")
    st.write("Ask questions about stock analysis and sentiment")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process the query
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                # Get analysis from stock_analyzer
                analysis_result = analyze_stock_query(prompt)
                # Display only the refined response
                st.markdown(analysis_result["refined_response"])
                print(analysis_result["refined_response"])
                st.session_state.messages.append({"role": "assistant", "content": analysis_result["refined_response"]})

if __name__ == "__main__":
    main() 