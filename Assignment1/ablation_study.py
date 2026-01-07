import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, f1_score, confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def calculate_metrics(df, prediction_col, actual_col='stars'):
    """
    Calculate comprehensive metrics for a prediction method
    """
    # Filter out rows with missing predictions
    valid_mask = df[prediction_col].notna()
    y_true = df.loc[valid_mask, actual_col]
    y_pred = df.loc[valid_mask, prediction_col]
    
    # Convert to int to ensure proper comparison
    y_true = y_true.astype(int)
    y_pred = y_pred.astype(int)
    
    # Calculate metrics
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[1, 2, 3, 4, 5])
    
    # Per-class metrics
    class_report = classification_report(y_true, y_pred, labels=[1, 2, 3, 4, 5], 
                                        target_names=['1-star', '2-star', '3-star', '4-star', '5-star'],
                                        output_dict=True, zero_division=0)
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'f1_score': f1,
        'confusion_matrix': cm,
        'classification_report': class_report,
        'n_samples': len(y_true)
    }

def plot_confusion_matrix(cm, method_name, save_path):
    """
    Plot and save confusion matrix
    """
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=[1, 2, 3, 4, 5],
                yticklabels=[1, 2, 3, 4, 5])
    plt.title(f'Confusion Matrix - {method_name}')
    plt.ylabel('True Stars')
    plt.xlabel('Predicted Stars')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved confusion matrix to {save_path}")

def print_metrics_table(methods_metrics):
    """
    Print a comparison table of all metrics
    """
    print("\n" + "="*80)
    print("ABLATION STUDY - COMPREHENSIVE METRICS COMPARISON")
    print("="*80)
    
    # Overall metrics table
    print("\n" + "-"*80)
    print(f"{'Method':<25} {'Accuracy':<12} {'Precision':<12} {'F1-Score':<12} {'Samples':<10}")
    print("-"*80)
    
    for method, metrics in methods_metrics.items():
        print(f"{method:<25} {metrics['accuracy']:<12.4f} {metrics['precision']:<12.4f} "
              f"{metrics['f1_score']:<12.4f} {metrics['n_samples']:<10}")
    
    print("-"*80)
    
    # Find best method for each metric
    best_accuracy = max(methods_metrics.items(), key=lambda x: x[1]['accuracy'])
    best_precision = max(methods_metrics.items(), key=lambda x: x[1]['precision'])
    best_f1 = max(methods_metrics.items(), key=lambda x: x[1]['f1_score'])
    
    print(f"\n🏆 Best Accuracy:  {best_accuracy[0]} ({best_accuracy[1]['accuracy']:.4f})")
    print(f"🏆 Best Precision: {best_precision[0]} ({best_precision[1]['precision']:.4f})")
    print(f"🏆 Best F1-Score:  {best_f1[0]} ({best_f1[1]['f1_score']:.4f})")

def print_per_class_metrics(methods_metrics):
    """
    Print per-class metrics for each method
    """
    print("\n" + "="*80)
    print("PER-CLASS PERFORMANCE ANALYSIS")
    print("="*80)
    
    for method, metrics in methods_metrics.items():
        print(f"\n{method}")
        print("-" * 80)
        print(f"{'Class':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
        print("-" * 80)
        
        report = metrics['classification_report']
        for star in ['1-star', '2-star', '3-star', '4-star', '5-star']:
            if star in report:
                print(f"{star:<12} {report[star]['precision']:<12.4f} "
                      f"{report[star]['recall']:<12.4f} "
                      f"{report[star]['f1-score']:<12.4f} "
                      f"{int(report[star]['support']):<10}")
        
        # Macro and weighted averages
        print("-" * 80)
        print(f"{'Macro Avg':<12} {report['macro avg']['precision']:<12.4f} "
              f"{report['macro avg']['recall']:<12.4f} "
              f"{report['macro avg']['f1-score']:<12.4f}")
        print(f"{'Weighted Avg':<12} {report['weighted avg']['precision']:<12.4f} "
              f"{report['weighted avg']['recall']:<12.4f} "
              f"{report['weighted avg']['f1-score']:<12.4f}")

def print_confusion_matrices(methods_metrics):
    """
    Print confusion matrices in text format
    """
    print("\n" + "="*80)
    print("CONFUSION MATRICES")
    print("="*80)
    
    for method, metrics in methods_metrics.items():
        print(f"\n{method}")
        print("-" * 50)
        cm = metrics['confusion_matrix']
        
        # Header
        print(f"{'True/Pred':<12}", end='')
        for i in range(1, 6):
            print(f"{i:>8}", end='')
        print()
        print("-" * 50)
        
        # Rows
        for i, row in enumerate(cm, 1):
            print(f"{i}-star{'':<6}", end='')
            for val in row:
                print(f"{val:>8}", end='')
            print()

def save_summary_report(methods_metrics, output_file='ablation_study_report.txt'):
    """
    Save a comprehensive text report
    """
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("ABLATION STUDY - COMPREHENSIVE EVALUATION REPORT\n")
        f.write("="*80 + "\n\n")
        
        # Overall metrics
        f.write("OVERALL METRICS\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Method':<25} {'Accuracy':<12} {'Precision':<12} {'F1-Score':<12}\n")
        f.write("-"*80 + "\n")
        
        for method, metrics in methods_metrics.items():
            f.write(f"{method:<25} {metrics['accuracy']:<12.4f} {metrics['precision']:<12.4f} "
                   f"{metrics['f1_score']:<12.4f}\n")
        
        f.write("\n\nDETAILED PER-CLASS METRICS\n")
        f.write("="*80 + "\n")
        
        for method, metrics in methods_metrics.items():
            f.write(f"\n{method}\n")
            f.write("-" * 80 + "\n")
            
            report = metrics['classification_report']
            for star in ['1-star', '2-star', '3-star', '4-star', '5-star']:
                if star in report:
                    f.write(f"{star}: Precision={report[star]['precision']:.4f}, "
                           f"Recall={report[star]['recall']:.4f}, "
                           f"F1={report[star]['f1-score']:.4f}, "
                           f"Support={int(report[star]['support'])}\n")
    
    print(f"\nSaved detailed report to {output_file}")

def main():
    # Load the results CSV
    input_file = 'yelp_zero_shot_results.csv'
    
    if not Path(input_file).exists():
        print(f"Error: {input_file} not found. Please run the prediction scripts first.")
        return
    
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # Dictionary to store metrics for each method
    methods_metrics = {}
    
    # Calculate metrics for each method
    if 'zero_shot_predicted_stars' in df.columns:
        print("Calculating metrics for Zero-Shot...")
        methods_metrics['Zero-Shot'] = calculate_metrics(df, 'zero_shot_predicted_stars')
    
    if 'few_shot_predicted_stars' in df.columns:
        print("Calculating metrics for Few-Shot...")
        methods_metrics['Few-Shot'] = calculate_metrics(df, 'few_shot_predicted_stars')
    
    if 'cot_predicted_stars' in df.columns:
        print("Calculating metrics for Chain-of-Thought...")
        methods_metrics['Chain-of-Thought'] = calculate_metrics(df, 'cot_predicted_stars')
    
    if not methods_metrics:
        print("No prediction columns found in the CSV!")
        return
    
    # Print comprehensive metrics
    print_metrics_table(methods_metrics)
    print_per_class_metrics(methods_metrics)
    print_confusion_matrices(methods_metrics)
    
    # Create output directory for plots
    output_dir = Path('ablation_study_results')
    output_dir.mkdir(exist_ok=True)
    
    # Generate and save confusion matrix plots
    print("\n" + "="*80)
    print("GENERATING CONFUSION MATRIX PLOTS")
    print("="*80)
    
    for method, metrics in methods_metrics.items():
        safe_method_name = method.lower().replace('-', '_').replace(' ', '_')
        plot_path = output_dir / f'confusion_matrix_{safe_method_name}.png'
        plot_confusion_matrix(metrics['confusion_matrix'], method, plot_path)
    
    # Save comprehensive report
    report_path = output_dir / 'ablation_study_report.txt'
    save_summary_report(methods_metrics, report_path)
    
    # Create comparison visualization
    print("\nGenerating comparison chart...")
    create_comparison_chart(methods_metrics, output_dir / 'metrics_comparison.png')
    
    print("\n" + "="*80)
    print("ABLATION STUDY COMPLETE")
    print("="*80)
    print(f"\nAll results saved to: {output_dir}/")
    print("Files generated:")
    print("  - confusion_matrix_*.png (one for each method)")
    print("  - metrics_comparison.png")
    print("  - ablation_study_report.txt")

def create_comparison_chart(methods_metrics, save_path):
    """
    Create a bar chart comparing all metrics across methods
    """
    methods = list(methods_metrics.keys())
    accuracies = [methods_metrics[m]['accuracy'] for m in methods]
    precisions = [methods_metrics[m]['precision'] for m in methods]
    f1_scores = [methods_metrics[m]['f1_score'] for m in methods]
    
    x = np.arange(len(methods))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    bars1 = ax.bar(x - width, accuracies, width, label='Accuracy', color='#3498db')
    bars2 = ax.bar(x, precisions, width, label='Precision', color='#2ecc71')
    bars3 = ax.bar(x + width, f1_scores, width, label='F1-Score', color='#e74c3c')
    
    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('Ablation Study - Metrics Comparison Across Methods', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend()
    ax.set_ylim([0, 1.0])
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.3f}',
                   ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved comparison chart to {save_path}")

if __name__ == "__main__":
    main()
