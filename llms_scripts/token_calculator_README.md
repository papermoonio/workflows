# Token Calculator

A Python script that calculates the number of AI tokens for every `.txt` or `.md` file in a given directory.

## Features

- Counts tokens using tiktoken with selectable encodings
- Uses cl100k_base encoding by default (good for most AI models)
- Adds 5% adjustment to token count for better cross-model approximation
- Shows all files with their token counts
- Highlights files above a specified token threshold (default: 200,000)
- Supports multiple tiktoken encodings (cl100k_base, p50k_base, gpt2)
- Recursive directory scanning option
- CSV export option
- Clean tabular output format

## Installation

Make sure you have the required dependencies installed:

```bash
pip install tiktoken
```

Or install all requirements from the main directory:

```bash
pip install -r ../requirements.txt
```

## Usage

### Basic Usage

Calculate tokens for all .txt and .md files in a directory:

```bash
python calculate_tokens.py /path/to/your/directory
```

### Advanced Usage

With recursive scanning and specific encoding:

```bash
python calculate_tokens.py /path/to/your/directory --recursive --encoding cl100k_base
```

With custom threshold and different encoding:

```bash
python calculate_tokens.py /path/to/your/directory --threshold 100000 --encoding p50k_base
```

Export results to CSV:

```bash
python calculate_tokens.py /path/to/your/directory --output results.csv
```

### Available Options

- `directory`: Path to the directory to scan (required)
- `--encoding`: Tiktoken encoding to use (default: cl100k_base)
- `--threshold`: Highlight files with more than this many tokens (default: 200000)
- `--recursive`: Search subdirectories recursively
- `--output`: Save results to CSV file

### Supported Encodings

- `cl100k_base`: GPT-4, GPT-3.5-turbo (default, good general approximation)
- `p50k_base`: GPT-3 davinci, curie, babbage, ada
- `gpt2`: GPT-2

*Note: All token counts include a 5% adjustment to provide better approximation for different AI model tokenizations.*

## Example Output

```
Found 15 text files to process...
Using encoding: cl100k_base (with 5% adjustment)
Files above 200,000 tokens are marked with ⚠️
--------------------------------------------------------------------------------
File                                              Tokens       Status
--------------------------------------------------------------------------------
README.md                                          1,296       ✓
docs/guide.md                                      2,579       ✓
large_document.md                                257,961       ⚠️
technical_guide.md                               199,045       ✓
api_reference.md                                 246,179       ⚠️
tutorial.md                                       12,962       ✓
FAQ.md                                             9,346       ✓
...
--------------------------------------------------------------------------------
⚠️  Found 2 files above the threshold of 200,000 tokens.
```

## Use Cases

- **Context Limit Planning**: Identify files that exceed AI model context limits
- **Cross-Model Approximation**: Use cl100k_base with 5% adjustment as general approximation for most AI models
- **Documentation Analysis**: Analyze the size and complexity of documentation
- **Content Optimization**: Find files that need splitting for AI processing
- **Project Analysis**: Get token statistics for entire documentation projects
- **Threshold Monitoring**: Quickly spot files above your specified token limit

## Token Limits Reference

Common AI model token limits:
- GPT-3.5-turbo: 4,096 tokens (input + output)
- GPT-4: 8,192 tokens (input + output)
- GPT-4-32k: 32,768 tokens (input + output)
- Claude-3: 200,000 tokens
- Claude-3.5-Sonnet: 200,000 tokens

## Notes

- The script uses UTF-8 encoding and ignores encoding errors
- Binary files are skipped automatically
- Token counts include a 5% adjustment to provide better approximation across different AI models
- cl100k_base encoding works well as a general approximation for most modern AI models
- Files above the threshold are marked with ⚠️ for easy identification
- All files are shown regardless of threshold, but flagged appropriately
- Different encodings can be selected for specific model families if needed