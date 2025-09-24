#!/usr/bin/env python3
"""
Token Calculator Script

This script calculates the number of AI tokens for every txt or md file in a given directory.
It uses tiktoken for accurate token counting based on OpenAI's encoding methods.

Usage:
    python calculate_tokens.py <directory_path> [--encoding <encoding_name>] [--recursive]

Example:
    python calculate_tokens.py /path/to/documents --encoding cl100k_base --recursive
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import tiktoken
from dataclasses import dataclass


@dataclass
class FileTokenInfo:
    """Data class to store file token information"""
    file_path: str
    file_size_bytes: int
    token_count: int
    character_count: int
    word_count: int


class TokenCalculator:
    """Token calculator for text files"""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize the token calculator with a specific encoding.
        
        Args:
            encoding_name: The tiktoken encoding to use (default: cl100k_base for general approximation)
        """
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
            self.encoding_name = encoding_name
        except KeyError:
            print(f"Warning: Encoding '{encoding_name}' not found. Using 'cl100k_base'")
            self.encoding = tiktoken.get_encoding("cl100k_base")
            self.encoding_name = "cl100k_base"
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text with 5% bump for approximation accuracy"""
        try:
            base_tokens = len(self.encoding.encode(text))
            # Add 5% to account for potential differences in other model tokenizations
            adjusted_tokens = int(base_tokens * 1.05)
            return adjusted_tokens
        except Exception as e:
            print(f"Error encoding text: {e}")
            return 0
    
    def count_words(self, text: str) -> int:
        """Count words in the given text"""
        return len(text.split())
    
    def process_file(self, file_path: Path) -> FileTokenInfo:
        """
        Process a single file and return token information.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            FileTokenInfo object with token and file statistics
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            token_count = self.count_tokens(content)
            character_count = len(content)
            word_count = self.count_words(content)
            file_size = file_path.stat().st_size
            
            return FileTokenInfo(
                file_path=str(file_path),
                file_size_bytes=file_size,
                token_count=token_count,
                character_count=character_count,
                word_count=word_count
            )
        
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return FileTokenInfo(
                file_path=str(file_path),
                file_size_bytes=0,
                token_count=0,
                character_count=0,
                word_count=0
            )
    
    def find_text_files(self, directory: Path, recursive: bool = False) -> List[Path]:
        """
        Find all txt and md files in the given directory.
        
        Args:
            directory: Directory to search
            recursive: Whether to search recursively
            
        Returns:
            List of Path objects for found files
        """
        text_files = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md']:
                text_files.append(file_path)
        
        return sorted(text_files)
    
    def calculate_directory_tokens(self, directory_path: str, recursive: bool = False, threshold: int = 200000) -> List[FileTokenInfo]:
        """
        Calculate tokens for all text files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to search recursively
            threshold: Only show files above this token threshold
            
        Returns:
            List of FileTokenInfo objects
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")
        
        text_files = self.find_text_files(directory, recursive)
        
        if not text_files:
            print(f"No .txt or .md files found in {directory_path}")
            return []
        
        print(f"Found {len(text_files)} text files to process...")
        print(f"Using encoding: {self.encoding_name} (with 5% adjustment)")
        print(f"Files above {threshold:,} tokens are marked with ⚠️")
        print("-" * 80)
        print(f"{'File':<50} {'Tokens':<12} {'Status':<6}")
        print("-" * 80)
        
        results = []
        files_above_threshold = 0
        
        for file_path in text_files:
            file_info = self.process_file(file_path)
            results.append(file_info)
            
            relative_path = file_path.relative_to(directory)
            filename = str(relative_path)[:47] + "..." if len(str(relative_path)) > 50 else str(relative_path)
            
            # Mark files above threshold
            if file_info.token_count > threshold:
                files_above_threshold += 1
                status = "⚠️"
            else:
                status = "✓"
            
            print(f"{filename:<50} {file_info.token_count:>11,} {status:<6}")
        
        print("-" * 80)
        if files_above_threshold == 0:
            print(f"✅ All files are below the threshold of {threshold:,} tokens.")
        else:
            print(f"⚠️  Found {files_above_threshold} files above the threshold of {threshold:,} tokens.")
        
        return results
    



def main():
    """Main function to handle command line arguments and run the token calculator"""
    parser = argparse.ArgumentParser(
        description="Calculate AI tokens for txt and md files in a directory, highlighting files above threshold",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python calculate_tokens.py /path/to/docs
  python calculate_tokens.py /path/to/docs --recursive --threshold 100000
  python calculate_tokens.py /path/to/docs --encoding gpt2 --threshold 50000
  python calculate_tokens.py /path/to/docs --encoding cl100k_base --output results.csv

Available encodings:
  - cl100k_base (GPT-4, GPT-3.5-turbo) - default with 5% adjustment
  - p50k_base (GPT-3 davinci, curie, babbage, ada)
  - gpt2 (GPT-2)

Token counts include a 5% adjustment for better approximation across AI models.
        """
    )
    
    parser.add_argument(
        "directory",
        help="Directory path to scan for txt and md files"
    )
    
    parser.add_argument(
        "--encoding",
        default="cl100k_base",
        help="Tiktoken encoding to use (default: cl100k_base)"
    )
    
    parser.add_argument(
        "--threshold",
        type=int,
        default=200000,
        help="Highlight files with more than this many tokens (default: 200000)"
    )
    
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search for files recursively in subdirectories"
    )
    
    parser.add_argument(
        "--output",
        help="Optional: Save results to CSV file"
    )
    
    args = parser.parse_args()
    
    try:
        calculator = TokenCalculator(args.encoding)
        results = calculator.calculate_directory_tokens(args.directory, args.recursive, args.threshold)
        
        # Save to CSV if requested
        if args.output:
            save_to_csv(results, args.output)
            print(f"\nResults saved to: {args.output}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def save_to_csv(results: List[FileTokenInfo], output_path: str):
    """Save results to a CSV file"""
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['file_path', 'file_size_bytes', 'token_count', 'character_count', 'word_count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow({
                'file_path': result.file_path,
                'file_size_bytes': result.file_size_bytes,
                'token_count': result.token_count,
                'character_count': result.character_count,
                'word_count': result.word_count
            })


if __name__ == "__main__":
    main()