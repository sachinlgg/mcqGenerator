import os
import json 
import traceback
import pandas as pd
from dotenv import load_dotenv
from src.mcqgenerator.utils import read_file, get_table_data
from src.mcqgenerator.logger import logging

# Importing necessary packages from langchain
# from langchain.chat_models import ChatOpenAI
# from langchain_community.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain

# Load environment cariables from the .env file
load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')

llm = ChatOpenAI(openai_api_key=openai_api_key, model_name='gpt-3.5-turbo', temperature=0.5)

QUIZ_TEMPLATE = """
Text: {text}
You are an expert MCQ maker. Given the above text, it is your job to \
create a quiz of {number} mulitple choice questions for {subject} \
students in {tone} tone. 
Make sure the questions are not repeated and check all the questions \
to be conforming the text as well. 
Make sure to format your response like RESPONSE_JSON below and use it as \
a guide. Ensure to make {number} MCQs. Also ensure you ouput json only and its keys and values are in double quotes always.

### RESPONSE_JSON
{response_json}
"""

quiz_generation_prompt = PromptTemplate(
    input_variables=['text', 'number', 'subject', 'tone', 'response_json'],
    template=QUIZ_TEMPLATE
)

quiz_chain = LLMChain(llm=llm, prompt=quiz_generation_prompt, output_key='quiz', verbose=True)

QUIZ_EVAL_TEMPLATE = """
You are an expert english grammarian and writer. Given a Multiple Choice Quiz for {subject} students.\
You need to evaluate the complexity of the question and give a complete analysis of the quiz if the students
will be able to unserstand the questions and answer them. Only use at max 50 words for complexity analysis. 
if the quiz is not at par with the cognitive and analytical abilities of the students,\
update each quiz questions which needs to be changed  and change the tone such that it perfectly fits the student abilities
Quiz_MCQs:
{quiz}

Check from an expert English Writer of the above quiz:
"""

quiz_evaluation_prompt = PromptTemplate(
    input_variables=['subject', 'quiz'],
    template=QUIZ_EVAL_TEMPLATE
)

review_chain = LLMChain(llm=llm, prompt=quiz_evaluation_prompt, verbose=True, output_key='review')

gen_eval_quiz_seq_chain = SequentialChain(
    chains=[quiz_chain, review_chain], 
    input_variables=['text', 'number', 'subject', 'tone', 'response_json'],
    output_variables=['quiz', 'review'], 
    verbose=True
)

