#!/usr/bin/env python3
"""
This script modifies the rental_scraper.py and sales_scraper.py files
to update existing CSV files in the data folder instead of creating new ones.
"""
import os
import re

def modify_scraper(file_path, output_file_pattern, new_output_path):
    """
    Modify a scraper file to use a fixed output path instead of date-based filenames.
    
    Args:
        file_path: Path to the scraper file
        output_file_pattern: Regex pattern to match the output file line
        new_output_path: New path where data should be saved
    """
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} does not exist")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Modify the output file path
    modified_content = re.sub(
        output_file_pattern,
        f'output_file = "{new_output_path}"',
        content
    )
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(new_output_path), exist_ok=True)
    
    # Write the modified content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"Modified {file_path} to save data to {new_output_path}")
    return True

def main():
    # Create the .github/scripts directory if it doesn't exist
    os.makedirs('.github/scripts', exist_ok=True)
    
    # Move this script to the .github/scripts directory if it's not already there
    current_file = os.path.abspath(__file__)
    target_location = os.path.abspath('.github/scripts/update_scrapers.py')
    
    if current_file != target_location and not os.path.exists(target_location):
        with open(current_file, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        with open(target_location, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"Copied this script to {target_location}")
    
    # Modify the rental scraper
    modify_scraper(
        'rental_scraper.py', 
        r'output_file = f"unegui_data_\{date\.today\(\)\.strftime\(\'%Y%m%d\'\)\}\.csv"',
        'data/unegui_rental_data.csv'
    )
    
    # Modify the sales scraper
    modify_scraper(
        'sales_scraper.py', 
        r'output_file = f"unegui_sales_data_\{date\.today\(\)\.strftime\(\'%Y%m%d\'\)\}\.csv"', 
        'data/unegui_sales_data.csv'
    )
    
    # Modify the load_existing_data methods to point to the fixed file locations
    rental_load_pattern = r'files = \[f for f in os\.listdir\(\'\.\'\) if f\.startswith\(\'unegui_data_\'\) and f\.endswith\(\'\.csv\'\)\]'
    sales_load_pattern = r'files = \[f for f in os\.listdir\(\'\.\'\) if f\.startswith\(\'unegui_sales_data_\'\) and f\.endswith\(\'\.csv\'\)\]'
    
    with open('rental_scraper.py', 'r', encoding='utf-8') as f:
        rental_content = f.read()
    
    modified_rental = re.sub(
        rental_load_pattern,
        'return pd.read_csv("data/unegui_rental_data.csv", encoding="utf-8-sig") if os.path.exists("data/unegui_rental_data.csv") else pd.DataFrame()',
        rental_content
    )
    modified_rental = re.sub(
        r'if not files:\s+return pd\.DataFrame\(\)\s+\s+latest_file = max\(files\)\s+df = pd\.read_csv\(latest_file, encoding=\'utf-8-sig\'\)',
        'df = pd.DataFrame()',
        modified_rental
    )
    
    with open('rental_scraper.py', 'w', encoding='utf-8') as f:
        f.write(modified_rental)
    
    with open('sales_scraper.py', 'r', encoding='utf-8') as f:
        sales_content = f.read()
    
    modified_sales = re.sub(
        sales_load_pattern,
        'return pd.read_csv("data/unegui_sales_data.csv", encoding="utf-8-sig") if os.path.exists("data/unegui_sales_data.csv") else pd.DataFrame()',
        sales_content
    )
    modified_sales = re.sub(
        r'if not files:\s+return pd\.DataFrame\(\)\s+\s+latest_file = max\(files\)\s+df = pd\.read_csv\(latest_file, encoding=\'utf-8-sig\'\)',
        'df = pd.DataFrame()',
        modified_sales
    )
    
    with open('sales_scraper.py', 'w', encoding='utf-8') as f:
        f.write(modified_sales)
    
    print("Modified both scrapers to use fixed file paths in the data directory")

if __name__ == "__main__":
    main()
