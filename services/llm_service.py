from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from config import HF_TOKEN

# Meta-Llama-3.1-8B for fast classifications and query generation
llm_fast = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    max_new_tokens=120,
    temperature=0.1,
)
chat_fast = ChatHuggingFace(llm=llm_fast)

# Meta-Llama-3.3-70B for creative generation (marketing, copywriting, branding, pricing)
llm_creative = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.3-70B-Instruct",
    max_new_tokens=1000,
    temperature=0.7,
)
chat_creative = ChatHuggingFace(llm=llm_creative)
