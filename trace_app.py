import sys
import time

print("1. Importing basic libraries...")
import os
import io
import json
import base64
import logging
import hashlib
print("   Done.")

print("2. Importing web & DB libraries...")
import fastapi
import uvicorn
import pydantic
import gradio as gr
import pyodbc
import redis
import httpx
print("   Done.")

print("3. Importing LangChain & LangGraph...")
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
print("   Done.")

print("4. Testing SQL Server connection...")
DB_CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=db39807.public.databaseasp.net;"
    "Database=db39807;"
    "Uid=db39807;"
    "Pwd=Ya8@_Dt4o9N=;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=10;" # Reduced timeout for quick testing
)
try:
    t0 = time.time()
    conn = pyodbc.connect(DB_CONN_STR)
    print(f"   SQL Server Connected in {time.time()-t0:.2f}s!")
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 BusinessName FROM BusinessOwnerProfile")
    row = cursor.fetchone()
    print(f"   Fetch test: {row[0]}")
    conn.close()
except Exception as e:
    print(f"   SQL Server Failed: {e}")

print("5. Testing Redis connection...")
try:
    t0 = time.time()
    r = redis.Redis(host="127.0.0.1", port=6379, socket_timeout=2)
    r.ping()
    print(f"   Redis Connected in {time.time()-t0:.2f}s!")
except Exception as e:
    print(f"   Redis Failed (Fallback to local is expected): {e}")

print("6. Testing HuggingFaceEndpoint instantiation...")
try:
    t0 = time.time()
    llm = HuggingFaceEndpoint(
        repo_id="meta-llama/Llama-3.1-8B-Instruct",
        max_new_tokens=20,
        temperature=0.1,
    )
    print(f"   HuggingFaceEndpoint instantiated in {time.time()-t0:.2f}s!")
    
    print("7. Testing ChatHuggingFace instantiation...")
    t0 = time.time()
    chat = ChatHuggingFace(llm=llm)
    print(f"   ChatHuggingFace instantiated in {time.time()-t0:.2f}s!")
except Exception as e:
    print(f"   Hugging Face instantiation failed: {e}")

print("Diagnostics complete!")
