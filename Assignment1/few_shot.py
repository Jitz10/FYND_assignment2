import pandas as pd
import json
import os
from groq import Groq
from dotenv import load_dotenv
from tqdm import tqdm
import time

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))
MODEL_NAME = os.getenv('MODEL_NAME')

def few_shot_predict(review_text):
    """
    Few-shot prediction with structured reasoning and examples
    """
    prompt = f"""You are an expert Yelp review classifier. Your task is to predict the star rating (1-5) based on the review text.

RATING GUIDELINES:
★☆☆☆☆ (1 star): Extremely negative, multiple severe issues, strong anger/frustration, would never return
★★☆☆☆ (2 stars): Mostly negative with significant problems, disappointed, might mention 1 small positive aspect
★★★☆☆ (3 stars): Mixed or neutral, "okay/decent/average", has both positives and negatives balanced
★★★★☆ (4 stars): Mostly positive with minor issues, satisfied, would recommend with small reservations
★★★★★ (5 stars): Extremely positive, enthusiastic praise, exceptional experience, highly recommends

EXAMPLES:

Review: "Absolutely disgusting. Found hair in my food, the manager was rude when I complained, and they still charged me full price. The whole place smelled bad and looked dirty. Never coming back and telling everyone to avoid this place."
{{"predicted_stars": 1, "explanation": "Multiple severe complaints (hygiene, service, cleanliness), strong negative emotion, explicit warning to others"}}

Review: "Pretty disappointed. Food took 45 minutes to arrive and was cold. The waiter forgot our drinks twice. The pasta was bland and overpriced. Only positive was the bread was okay."
{{"predicted_stars": 2, "explanation": "Predominantly negative experience with service and food quality issues, one minor positive doesn't offset major problems"}}

Review: "It's an okay place. Nothing special but nothing terrible either. Food was decent, service was average. Prices are reasonable. I'd go back if friends wanted to, but wouldn't seek it out myself."
{{"predicted_stars": 3, "explanation": "Neutral tone throughout, repetitive 'average/okay/decent' language, no strong feelings either way"}}

Review: "Really enjoyed our meal! The steak was cooked perfectly and the sides were delicious. Service was attentive and friendly. Only complaint is it was a bit noisy, but that's minor. Would definitely come back."
{{"predicted_stars": 4, "explanation": "Strong positive experience with specific praise, one small negative mentioned but dismissed as minor, clear intent to return"}}

Review: "WOW! Best dining experience I've had in years! Every dish was phenomenal - the chef clearly knows what they're doing. Our server made excellent recommendations and the atmosphere was perfect. Can't wait to bring my family here. Absolutely worth every penny!"
{{"predicted_stars": 5, "explanation": "Extreme enthusiasm with exclamation marks, superlatives (best/phenomenal/perfect), multiple aspects praised, emotional excitement, strong recommendation"}}

Review: "The service was incredibly slow and our order was wrong. When we told them, they argued with us instead of fixing it. Food was mediocre at best and way overpriced for what you get."
{{"predicted_stars": 2, "explanation": "Multiple significant issues (service, accuracy, value), defensive staff response, no redeeming qualities mentioned"}}

Review: "Great little spot! Food is consistently good and the staff remembers us. Prices are fair and portions are generous. The only thing is parking can be tricky on weekends."
{{"predicted_stars": 4, "explanation": "Multiple positive aspects with specific details, loyalty indicated, minor inconvenience mentioned but doesn't diminish overall satisfaction"}}

Now classify this review:

Review: {review_text}

Return ONLY valid JSON in this exact format:
{{
  "predicted_stars": <integer 1-5>,
  "explanation": "<concise reasoning in under 100 characters>"
}}"""
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=MODEL_NAME,
            temperature=0.1,
            max_tokens=300,
        )
        
        response_text = chat_completion.choices[0].message.content
        
        # Try to parse JSON from response
        # Sometimes the model wraps JSON in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        return result['predicted_stars'], result['explanation']
    
    except Exception as e:
        print(f"Error processing review: {e}")
        print(f"Response was: {response_text if 'response_text' in locals() else 'No response'}")
        return None, f"Error: {str(e)}"

def main():
    # Load the zero-shot results
    input_file = 'yelp_zero_shot_results.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Please run zero_shot.py first.")
        return
    
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Initialize new columns for few-shot results
    df['few_shot_predicted_stars'] = None
    df['few_shot_explaination'] = None
    
    # Process each review
    print(f"Processing {len(df)} reviews with few-shot prompting...")
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        review_text = row['text']
        
        predicted_stars, explanation = few_shot_predict(review_text)
        
        df.at[idx, 'few_shot_predicted_stars'] = predicted_stars
        df.at[idx, 'few_shot_explaination'] = explanation
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Save updated CSV with both zero-shot and few-shot results
    output_file = 'yelp_zero_shot_results.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    
    # Print statistics
    print("\n=== Few-Shot Statistics ===")
    print(f"Total reviews processed: {len(df)}")
    
    # Calculate accuracy for few-shot (where prediction is not None)
    valid_predictions = df[df['few_shot_predicted_stars'].notna()]
    if len(valid_predictions) > 0:
        accuracy = (valid_predictions['few_shot_predicted_stars'] == valid_predictions['stars']).sum() / len(valid_predictions)
        print(f"Few-shot Accuracy: {accuracy:.2%}")
        
        # Show distribution of predictions
        print("\nFew-shot prediction distribution:")
        print(valid_predictions['few_shot_predicted_stars'].value_counts().sort_index())
    else:
        print("No valid predictions were made.")
    
    # Compare with zero-shot if available
    if 'zero_shot_predicted_stars' in df.columns:
        zero_shot_valid = df[df['zero_shot_predicted_stars'].notna()]
        if len(zero_shot_valid) > 0:
            zero_shot_accuracy = (zero_shot_valid['zero_shot_predicted_stars'] == zero_shot_valid['stars']).sum() / len(zero_shot_valid)
            print(f"\n=== Comparison ===")
            print(f"Zero-shot Accuracy: {zero_shot_accuracy:.2%}")
            print(f"Few-shot Accuracy: {accuracy:.2%}")
            print(f"Improvement: {(accuracy - zero_shot_accuracy):.2%}")

if __name__ == "__main__":
    main()
