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

def chain_of_thought_predict(review_text):
    """
    Chain of Thought prediction with step-by-step reasoning
    """
    prompt = f"""You are a review rating classifier. Analyze the following Yelp review step-by-step and predict its star rating (1-5).

Review: {review_text}

Think through this step-by-step:

Step 1: Identify the overall sentiment
- Is the language positive, negative, or neutral?
- What emotional tone is expressed (angry, happy, disappointed, enthusiastic, indifferent)?

Step 2: Analyze specific aspects mentioned
- Food quality: What specific comments about food?
- Service: How is the service described?
- Ambiance/atmosphere: Any mentions of the environment?
- Value/pricing: Comments about prices or value?

Step 3: Look for key indicators
- Superlatives (best, worst, amazing, terrible)
- Exclamation marks or emphatic language
- Words like "never again" or "highly recommend"
- Balance of positive vs negative points

Step 4: Determine the rating
- 1 star: Overwhelmingly negative, multiple severe issues, anger
- 2 stars: Mostly negative, significant disappointment, few positives
- 3 stars: Balanced/neutral, "okay/average/decent"
- 4 stars: Mostly positive, minor issues, would return
- 5 stars: Exceptional, enthusiastic praise, highly recommends

Based on your analysis, provide your prediction.

Return ONLY valid JSON in this exact format:
{{
  "predicted_stars": <integer 1-5>,
  "explanation": "<brief summary of your reasoning>"
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
            max_tokens=400,
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
    # Load the existing results
    input_file = 'yelp_zero_shot_results.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Please run zero_shot.py and few_shot.py first.")
        return
    
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Initialize new columns for chain of thought results
    df['cot_predicted_stars'] = None
    df['cot_explaination'] = None
    
    # Process each review
    print(f"Processing {len(df)} reviews with chain-of-thought prompting...")
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        review_text = row['text']
        
        predicted_stars, explanation = chain_of_thought_predict(review_text)
        
        df.at[idx, 'cot_predicted_stars'] = predicted_stars
        df.at[idx, 'cot_explaination'] = explanation
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    # Save updated CSV with all results
    output_file = 'yelp_zero_shot_results.csv'
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
    
    # Print comprehensive statistics
    print("\n" + "="*60)
    print("FINAL ACCURACY COMPARISON")
    print("="*60)
    
    actual_stars = df['stars']
    
    # Zero-shot accuracy
    if 'zero_shot_predicted_stars' in df.columns:
        zero_shot_valid = df[df['zero_shot_predicted_stars'].notna()]['zero_shot_predicted_stars']
        if len(zero_shot_valid) > 0:
            zero_shot_accuracy = (zero_shot_valid == actual_stars[:len(zero_shot_valid)]).sum() / len(zero_shot_valid)
            print(f"\n📊 Zero-Shot Accuracy: {zero_shot_accuracy:.2%}")
            print(f"   Valid predictions: {len(zero_shot_valid)}/{len(df)}")
    
    # Few-shot accuracy
    if 'few_shot_predicted_stars' in df.columns:
        few_shot_valid = df[df['few_shot_predicted_stars'].notna()]['few_shot_predicted_stars']
        if len(few_shot_valid) > 0:
            few_shot_accuracy = (few_shot_valid == actual_stars[:len(few_shot_valid)]).sum() / len(few_shot_valid)
            print(f"\n📊 Few-Shot Accuracy: {few_shot_accuracy:.2%}")
            print(f"   Valid predictions: {len(few_shot_valid)}/{len(df)}")
    
    # Chain of thought accuracy
    cot_valid = df[df['cot_predicted_stars'].notna()]['cot_predicted_stars']
    if len(cot_valid) > 0:
        cot_accuracy = (cot_valid == actual_stars[:len(cot_valid)]).sum() / len(cot_valid)
        print(f"\n📊 Chain-of-Thought Accuracy: {cot_accuracy:.2%}")
        print(f"   Valid predictions: {len(cot_valid)}/{len(df)}")
    
    # Comparison summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if 'zero_shot_predicted_stars' in df.columns and 'few_shot_predicted_stars' in df.columns:
        print(f"\nMethod Ranking:")
        accuracies = []
        if len(zero_shot_valid) > 0:
            accuracies.append(("Zero-Shot", zero_shot_accuracy))
        if len(few_shot_valid) > 0:
            accuracies.append(("Few-Shot", few_shot_accuracy))
        if len(cot_valid) > 0:
            accuracies.append(("Chain-of-Thought", cot_accuracy))
        
        accuracies.sort(key=lambda x: x[1], reverse=True)
        for i, (method, acc) in enumerate(accuracies, 1):
            print(f"{i}. {method}: {acc:.2%}")
        
        # Show improvements
        if len(few_shot_valid) > 0 and len(zero_shot_valid) > 0:
            improvement_fs = few_shot_accuracy - zero_shot_accuracy
            print(f"\nFew-Shot vs Zero-Shot: {improvement_fs:+.2%}")
        
        if len(cot_valid) > 0 and len(zero_shot_valid) > 0:
            improvement_cot = cot_accuracy - zero_shot_accuracy
            print(f"Chain-of-Thought vs Zero-Shot: {improvement_cot:+.2%}")
        
        if len(cot_valid) > 0 and len(few_shot_valid) > 0:
            improvement_cot_fs = cot_accuracy - few_shot_accuracy
            print(f"Chain-of-Thought vs Few-Shot: {improvement_cot_fs:+.2%}")
    
    # Distribution comparison
    print("\n" + "="*60)
    print("PREDICTION DISTRIBUTIONS")
    print("="*60)
    
    print("\nActual Stars Distribution:")
    print(df['stars'].value_counts().sort_index())
    
    if 'zero_shot_predicted_stars' in df.columns and len(zero_shot_valid) > 0:
        print("\nZero-Shot Predictions:")
        print(df['zero_shot_predicted_stars'].value_counts().sort_index())
    
    if 'few_shot_predicted_stars' in df.columns and len(few_shot_valid) > 0:
        print("\nFew-Shot Predictions:")
        print(df['few_shot_predicted_stars'].value_counts().sort_index())
    
    if len(cot_valid) > 0:
        print("\nChain-of-Thought Predictions:")
        print(df['cot_predicted_stars'].value_counts().sort_index())
    
    print("\n" + "="*60)
    print(f"All results saved to: {output_file}")
    print("="*60)

if __name__ == "__main__":
    main()
