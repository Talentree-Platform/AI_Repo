import gradio as gr
import pandas as pd
import sys
from pathlib import Path

# Add current directory to path so imports work exactly like your FastAPI app
sys.path.append(str(Path(__file__).parent))

from models.owner_recommender import OwnerRecommender
from utils.config import settings

# Global model instance
owner_model = None

# 1. Load the Owner Model
def load_model():
    global owner_model
    try:
        if settings.owner_model_path.exists():
            owner_model = OwnerRecommender.load(settings.owner_model_path)
            print("Owner model loaded successfully.")
        else:
            print("WARNING: Owner model not found.")
    except Exception as e:
        print(f"Error loading model: {e}")

# Load model when the app starts
load_model()

# 2. Define the function the Gradio button will trigger
def get_owner_recs(owner_id, top_k):
    if not owner_model or not owner_model.is_trained:
        return "Error: Owner model is not trained or loaded."
    
    try:
        recs = owner_model.predict(owner_id=int(owner_id), top_k=int(top_k))
        if not recs:
            return "No raw material recommendations found for this brand owner."
        return pd.DataFrame(recs)
    except Exception as e:
        return f"An error occurred: {str(e)}"

# 3. Create the Gradio User Interface
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🏭 AI Brand Owner Materials Recommendation
        Suggests raw materials for production forecasting and supply-chain optimization.
        """
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            owner_id_input = gr.Number(label="Enter Brand Owner ID", value=1, precision=0)
            owner_top_k = gr.Slider(minimum=1, maximum=20, value=5, step=1, label="Number of Recommendations")
            owner_btn = gr.Button("Forecast Materials", variant="primary")
        with gr.Column(scale=2):
            owner_output = gr.Dataframe(label="Recommended Raw Materials", interactive=False)
            
    owner_btn.click(fn=get_owner_recs, inputs=[owner_id_input, owner_top_k], outputs=owner_output)

# 4. Launch the app!
if __name__ == "__main__":
    demo.launch()
