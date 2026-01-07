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

def zero_shot_predict(review_text):
    """
    Zero-shot prediction with structured reasoning
    """
    prompt = f"""You are a review rating classifier. Analyze the following Yelp review and predict its star rating (1-5).

Review: {review_text}

Consider:
- Sentiment (positive/negative language)
- Specific complaints or praise
- Overall tone and emotion

Return JSON:
{{
  "predicted_stars": <1-5>,
  "explanation": "<brief reasoning>"
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
    # Load the original dataset
    print("Loading yelp.csv...")
    df = pd.read_csv('yelp.csv')
    
    # Sample 200 random reviews
    print("Sampling 200 random reviews...")
    df_sample = df.sample(n=200, random_state=42).copy()
    
    # Initialize new columns
    df_sample['zero_shot_predicted_stars'] = None
    df_sample['zero_shot_explaination'] = None
    
    # Process each review
    print(f"Processing {len(df_sample)} reviews with zero-shot prompting...")
    for idx, row in tqdm(df_sample.iterrows(), total=len(df_sample)):
        review_text = row['text']
        
        predicted_stars, explanation = zero_shot_predict(review_text)
        
        df_sample.at[idx, 'zero_shot_predicted_stars'] = predicted_stars
        df_sample.at[idx, 'zero_shot_explaination'] = explanation
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Save to new CSV
    output_file = 'yelp_zero_shot_results.csv'
    df_sample.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    
    # Print statistics
    print("\n=== Statistics ===")
    print(f"Total reviews processed: {len(df_sample)}")
    
    # Calculate accuracy (where prediction is not None)
    valid_predictions = df_sample[df_sample['zero_shot_predicted_stars'].notna()]
    if len(valid_predictions) > 0:
        accuracy = (valid_predictions['zero_shot_predicted_stars'] == valid_predictions['stars']).sum() / len(valid_predictions)
        print(f"Accuracy: {accuracy:.2%}")
        
        # Show distribution of predictions
        print("\nPrediction distribution:")
        print(valid_predictions['zero_shot_predicted_stars'].value_counts().sort_index())
        
        print("\nActual distribution:")
        print(valid_predictions['stars'].value_counts().sort_index())
    else:
        print("No valid predictions were made.")

if __name__ == "__main__":
    main()
