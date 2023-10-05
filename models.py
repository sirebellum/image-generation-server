from diffusers import DiffusionPipeline
import torch

model_id = "stabilityai/stable-diffusion-xl-base-1.0"
refiner_id = "stabilityai/stable-diffusion-xl-refiner-1.0"
def load_models(device="cuda", dtype=torch.float16):
    base = DiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=dtype,
        use_safetensors=True,
    ).to(device)
    refiner = DiffusionPipeline.from_pretrained(
        refiner_id,
        torch_dtype=dtype,
        text_encoder_2=base.text_encoder_2,
        vae=base.vae,
        use_safetensors=True,
    ).to(device)
    return base, refiner

def generate_image_from_prompt(base, refiner, prompt):
    high_noise_frac = 0.8
    image = base(
        prompt=prompt,
        num_inference_steps=40,
        denoising_end=high_noise_frac,
        output_type='latent',
    ).images
    image = refiner(
        prompt=prompt,
        num_inference_steps=40,
        denoising_start=high_noise_frac,
        image=image,
    ).images[0]
    return image