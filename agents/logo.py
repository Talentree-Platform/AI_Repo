import io
import base64
import logging
from huggingface_hub import InferenceClient
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage

from orchestrator.state import AgentState
from services.llm_service import chat_creative, chat_fast
from config import HF_TOKEN
from prompts.logo_prompt import get_logo_enhancement_prompt, get_logo_fallback_prompt

logger = logging.getLogger("talentree.agents.logo")

def prompt_enhancement_node(state: AgentState) -> dict:
    brand = state.get("brand_profile", {})
    messages = state.get("messages", [])
    
    system_prompt = get_logo_enhancement_prompt(
        brand_name=brand.get("name", "Unknown"),
        brand_category=brand.get("category", "Unknown"),
        brand_desc=brand.get("description", "Unknown")
    )
 
    full_messages = [SystemMessage(content=system_prompt)] + messages
    resp = chat_creative.invoke(full_messages)
    enhanced_prompt = resp.content.strip()
    return {
        "logo_prompt": enhanced_prompt,
        "agent_output": f"🎨 **Enhanced Prompt Generated!**\n\n`{enhanced_prompt}`\n\nTo generate this logo, click **'Generate Logo Image'** or type **'generate logo'**."
    }

def logo_generation_node(state: AgentState) -> dict:
    brand = state.get("brand_profile", {})
    brand_name = brand.get("name", "Brand")
    logo_prompt = state.get("logo_prompt", "")
    
    if not logo_prompt:
        # Fallback to quickly enhancing the raw query if no prompt has been generated
        db_prompt_str = get_logo_fallback_prompt(brand_name, state.get("current_query", ""))
        prompt = PromptTemplate.from_template(db_prompt_str)
        chain = prompt | chat_fast
        resp = chain.invoke({"brand_name": brand_name, "user_input": state.get("current_query")})
        logo_prompt = resp.content.strip()

    final_prompt = (
        f"{logo_prompt}, vector logo design, flat design, professional branding, "
        "white background, no shadows, no gradients, no noise, "
        "crisp clean lines, high resolution, sharp edges, "
        "no text, no letters, no watermark, no drop shadow, no blur, "
        "no realistic photo, no 3D render, no gradient background"
    )
    
    # Cascade fallback to ensure reliable generation
    IMAGE_MODELS = [
        "stabilityai/stable-diffusion-xl-base-1.0",
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-2-1",
        "runwayml/stable-diffusion-v1-5"
    ]
    
    client = InferenceClient(token=HF_TOKEN)
    image = None
    model_used = None
    
    for model_name in IMAGE_MODELS:
        try:
            logger.info(f"Attempting image generation with model: {model_name}")
            image = client.text_to_image(final_prompt, model=model_name)
            model_used = model_name
            logger.info(f"Image generation succeeded using model: {model_name}")
            break
        except Exception as ex:
            logger.warning(f"Image generation failed with model {model_name}: {ex}")
            continue

    if not image:
        return {"agent_output": "❌ All Hugging Face image generation models are currently overloaded. Please try again in a few moments."}
        
    try:
        safe_name = brand_name.lower().replace(" ", "_")
        filename = f"{safe_name}_logo.png"
        image.save(filename)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        img_html = f"<img src='data:image/png;base64,{image_base64}' style='width:250px; border-radius:8px; border:1px solid #ddd; margin:10px 0;' />"
        download_btn = f"<br/><a href='data:image/png;base64,{image_base64}' download='{safe_name}_logo.png' style='display:inline-block; padding:8px 12px; background-color:#1E3A8A; color:white; border-radius:6px; text-decoration:none; margin:10px 0; font-weight:bold;'>💾 Download Logo Image</a>"
        
        output_str = (
            f"🎉 **Logo generated successfully for {brand_name}!**\n\n"
            f"Prompt: `{logo_prompt}`\n\n"
            f"{img_html}{download_btn}"
        )
        return {
            "logo_base64": image_base64,
            "logo_prompt": logo_prompt,
            "agent_output": output_str
        }
    except Exception as e:
        logger.exception("Logo post-processing failed")
        return {"agent_output": f"❌ Logo post-processing failed: {str(e)}"}
