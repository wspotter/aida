from transformers import AutoModelForCausalLM, AutoTokenizer
import sounddevice as sd
import numpy as np
import pyttsx3
engine = pyttsx3.init()
# 1. Load the Model and Tokenizer
model_name = "canary-tts-0.5b-GGUF"  # Replace with your model name if different
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# 2. Define the Text to Speak
input_text = "Hello, how are you today?"

# 3. Prepare the Input for the Model
inputs = tokenizer(input_text, return_tensors="pt")

# 4. Generate the Output (Text to Audio)
def text_to_speech(pyttsx3):
    # Placeholder: Replace this with your actual TTS implementation
    # This example generates random audio data
    sample_rate = 44100  # Standard audio sample rate
    duration = 2  # Duration in seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    frequency = 440  # Frequency of the sine wave (A4 note)
    audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)  # Sine wave
    return audio_data, sample_rate

# 5. Process the Text and Play Audio
outputs = model.generate(**inputs)
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
audio_data, sample_rate = text_to_speech(generated_text)

# 6. Play the Audio
engine.play(audio_data, sample_rate)
engine.wait()  # Wait until audio is finished
