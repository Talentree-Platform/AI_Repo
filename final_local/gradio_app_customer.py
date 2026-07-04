import gradio as gr
import pandas as pd
import sys
from pathlib import Path

# Add current directory to path so imports work exactly like your FastAPI app
sys.path.append(str(Path(__file__).parent))

from models.customer_recommender import CustomerRecommender
from utils.config import settings

# Global model instance
customer_model = None

# 1. Load the Customer Model
def load_model():
    global customer_model
    try:
        if settings.customer_model_path.exists():
            customer_model = CustomerRecommender.load(settings.customer_model_path)
            print("Customer model loaded successfully.")
        else:
            print("WARNING: Customer model not found.")
    except Exception as e:
        print(f"Error loading model: {e}")

# Load model when the app starts
load_model()

# 2. Define the function the Gradio button will trigger
def get_customer_recs(customer_id, top_k):
    if not customer_model or not customer_model.is_trained:
        return "Error: Customer model is not trained or loaded."
    
    try:
        recs = customer_model.predict(customer_id=int(customer_id), top_k=int(top_k))
        if not recs:
            return "No recommendations found for this customer."
        return pd.DataFrame(recs)
    except Exception as e:
        return f"An error occurred: {str(e)}"

# 3. Create the Gradio User Interface
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🛒 AI Customer Recommendation System
        Suggests highly relevant products to customers based on purchase history and item similarity.
        """
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            cust_id_input = gr.Number(label="Enter Customer ID", value=1, precision=0)
            cust_top_k = gr.Slider(minimum=1, maximum=20, value=5, step=1, label="Number of Recommendations")
            cust_btn = gr.Button("Get Suggestions", variant="primary")
        with gr.Column(scale=2):
            cust_output = gr.Dataframe(label="Recommended Products", interactive=False)
            
    cust_btn.click(fn=get_customer_recs, inputs=[cust_id_input, cust_top_k], outputs=cust_output)

# 4. Launch the app!
if __name__ == "__main__":
    demo.launch()
