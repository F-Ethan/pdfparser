Parser Flow: 

EventParser → EventData
                ↓
           precincts → Precinct
                          ↓
                       contests → Contest
                                   ↓
                                candidates → Candidate


This guide is designed to assist you in cloning the repository, setting up the environment, and running the Python application developed to process Precinct First – Heart PDFs.

The application is specifically tailored for PDFs documents that follow a "Precinct First" structure, where—immediately following the header—each page lists the precinct details and ballots cast in a format such as:

Precinct 3040 (Ballots Cast: 356)

1001 379 of 1,760 registered voters = 21.53%

This structure enables the script to accurately extract and process election-related data from these reports. See the example below for a typical page header:

Note: If the script processes only the first 10 pages of your PDFs and produces limited output, the application is currently running in development mode. Check the last section for more

Heart PDF - Precinct First Pdf example

Other PDF - Precinct first example 
Note this script will still process this PDF as it is the same layout.  


Prerequisites
This guide assumes that the following tools are already installed and configured on your system:

Git: For cloning the repository.

Python: Version 3.8 or higher recommended (verify with python --version or python3 --version).

pip: Python package installer (typically included with Python installations).

1. Cloning the Repository
To begin, clone the repository to your local machine using Git.

Open a terminal (on macOS/Linux) or Command Prompt/PowerShell (on Windows).

Navigate to the directory where you wish to store the project (e.g., your Documents or Projects folder):

text



cd ~/path/to/your/preferred/location
Clone the repository by running the following command:

text



git clone https://github.com/F-Ethan/pdfparser.git
Once the cloning process completes, navigate into the project directory:

text



cd pdfparser
This will create a local copy of the repository containing the Python application and all necessary files.

2. Preparing the Input Directory
The repository's .gitignore file is configured to exclude the input/ directory. This ensures that PDF files containing potentially sensitive election data are not accidentally committed to version control.

Follow these steps to set up the input directory and add your files:

In the root of the cloned repository, create a new directory named input:

text



mkdir input
Place all Hart Precinct First PDFs you wish to process into this input/ directory.

You may include multiple PDF files in this folder.

The application is intentionally designed to process all PDFs in the input/ directory and combine their extracted data into a single output CSV file.

This batch-processing approach is particularly useful in scenarios where election results are split across multiple reports for the same event, such as:

A city-specific PDF combined with a broader county PDF.

Separate PDFs for each political party (e.g., Democratic, Republican, Green, etc.).

By processing all files together, the script consolidates the data into one comprehensive CSV, simplifying downstream analysis.

Important Notes:

Ensure that only the relevant Hart Precinct First PDFs (those with the green header and precinct-first structure) are placed in the input/ directory. Including incompatible files may lead to extraction errors.

Do not commit or push the input/ directory or its contents to the repository.

3. Setting Up the Virtual Environment and Installing Dependencies
To ensure a clean and isolated environment, use a virtual environment.

In the root directory of the cloned repository, create a virtual environment named venv:

text



python3 -m venv venv
Activate the virtual environment:

On macOS/Linux:

text



source venv/bin/activate
On Windows (using Command Prompt):

text



venv\Scripts\activate.bat
Or (using PowerShell):

text



venv\Scripts\Activate.ps1
You should now see (venv) prefixed to your terminal prompt, indicating the environment is active.

Upgrade pip (recommended for compatibility):

text



pip install --upgrade pip
Install the project and its dependencies in editable mode:

text



pip install -e .
Verification After installation, verify that the packages are available by running:

text



pip list | grep -E "pdfplumber|pandas|tqdm"
You should see the three dependencies listed.

Note: If you ever need to deactivate the virtual environment, simply run deactivate. Always ensure the virtual environment is activated before running the application.

This section follows directly after "Preparing the Input Directory" and prepares users for the final "Running the Application" section.

Regarding clarity and recommendations:

4. Running the Application
With the virtual environment activated and PDFs placed in the input/ directory, execute the script as follows:

Ensure the virtual environment is active (you should see (venv) in your terminal prompt). If not, activate it using the commands from the previous section.

Run the parsing script:

text



python -m scripts.parse_pdf
This command executes the module scripts/parse_pdf.py relative to the project root.

The script will:

Process all PDF files found in the input/ directory.

Combine the extracted precinct-level election data into a single CSV file.

Display progress information in the terminal (via tqdm).

Output and Logging

Output CSV: The consolidated results will be saved as Election_Results.csv in the newly created output/ directory (the script will create this directory if it does not exist). Note: Each run overwrites any existing Election_Results.csv file.

Logs: All runtime logs are written to the logs/ directory (also created automatically if needed). Note: Existing log files are overwritten at the start of each run to ensure a clean log for the current execution.

Verification After completion, check the following:

Open output/Election_Results.csv to confirm the extracted data.

Review files in the logs/ directory for detailed processing information or any warnings/errors.

Troubleshooting Tips

If no PDFs are processed, verify that compatible Hart Precinct First PDFs are present in the input/ directory.

In case of errors (e.g., PDF parsing issues), consult the latest log file in logs/ for diagnostic details.

Troubleshooting
This section addresses common issues that may arise during PDF processing. If the extracted data in output/Election_Results.csv appears incomplete or incorrect, the problem often stems from mismatches between the PDF text layout and the regular expressions (regex patterns) used in the application's parsing logic.

The parsing relies on specific regex patterns defined in the source code modules (located in the src/ directory) to identify and extract structured information. Hart Precinct First PDFs generally follow a consistent format, but variations in wording, spacing, or formatting across different elections, counties, or report generations can cause extraction failures.

For each issue below, review the relevant module and regex patterns. Adjust them as needed to match the exact text lines in your PDFs (preserving case sensitivity and spacing where applicable). After modifications, reinstall in editable mode (pip install -e .) and re-run the script.

1. Event Data Missing or Incorrect
Event-level information—such as election date, type, county, total ballots, and party—may not be extracted properly if the header text does not match the expected patterns.

Review the src/event.py module, which defines the EventData dataclass:

Python



@dataclass
class EventData:
    date: str = ""
    election_type: str = ""
    county: str = ""
    total_ballots: str = ""
    party: str = ""
This module contains a list of regex patterns designed to capture full lines containing this information from the PDF header or early pages.


 

Steps to Resolve:

Examine the PDF section where event data appears (e.g., election title, date, and county lines near the green header).

Compare the exact text against the patterns in event.py.

Ensure each pattern matches the complete relevant line.


 

2. Precinct Data Missing or Incorrect
Precinct identifiers and related statistics (e.g., ballots cast, registered voters) may fail to parse if the "Precinct First" line format deviates from expectations.

Review the src/precinct.py module, which defines the Precinct dataclass:

Python



@dataclass
class Precinct:
    number: str
    ballots_cast: str = ""
    registered_voters: str = ""
    overvotes: str = ""
    undervotes: str = ""
The associated regex patterns in this module target lines such as "Precinct 3040 (Ballots Cast: 356)" or voter turnout percentages.


Or



Steps to Resolve:

Examine the PDF section immediately following the green header on a results page.

Verify that the regex patterns capture the precinct number, ballots cast, and any additional statistics precisely.

[Insert screenshot here: Example PDF section showing a precinct line] [Insert screenshot here: Relevant code snippet from src/precinct.py showing regex patterns]

3. Contest Data Missing or Incorrect
Contest titles (e.g., race names) and summary statistics may not be extracted if the formatting varies.

Review the src/contest.py module, which defines the Contest dataclass:

Python



@dataclass
class Contest:
    title: str = ""
    party: Optional[str] = None
    cast_votes: str = ""
    overvotes: str = ""
    undervotes: str = ""
    modifier: str = ""
Regex patterns here identify contest headers and vote totals.

Steps to Resolve:

Locate the PDF section introducing a new contest or race.

Adjust patterns to match the exact contest title lines and summary rows.

[Insert screenshot here: Example PDF section showing a contest header and totals] [Insert screenshot here: Relevant code snippet from src/contest.py showing regex patterns]

4. Candidate Data Missing or Incorrect
Individual candidate names, parties, and vote breakdowns may fail to parse due to layout differences.

Review the src/candidate.py module, which defines the CandidateResult dataclass:

Python



@dataclass
class CandidateResult:
    name: str
    party: Optional[str] = None
    total_votes: str = ""
    early_votes: str = ""
    absentee_votes: str = ""
    election_day_votes: str = ""
Patterns target candidate lines and columnar vote data.

Steps to Resolve:

Examine the PDF section listing candidates and their vote counts.

Ensure regex patterns align with candidate names, parties, and vote categories.

[Insert screenshot here: Example PDF section showing candidate rows] [Insert screenshot here: Relevant code snippet from src/candidate.py showing regex patterns]

General Advice

Always check the latest log files in the logs/ directory for specific warnings or errors indicating which patterns failed.

Test changes incrementally with a single PDF to verify improvements before processing multiple files.

Configuration Options
The application includes a configuration file located at src/config.py, which allows for minor adjustments to runtime behavior and output settings without modifying the core parsing logic.

Recommended Usage:

For large PDF files, enable development mode initially to process only the first 10 pages. This allows quick verification of parsing accuracy without waiting for full execution.

Once satisfied with the results, disable development mode to process complete files.

Key configurable parameters include:

OUTPUT_CSV: Defines the path and filename of the generated results file (currently set to output/Election_Results.csv). To change the output filename or location, modify this line:

Python



OUTPUT_CSV = OUTPUT_DIR / "Your_Custom_Filename.csv"
INPUT_DIR, OUTPUT_DIR, LOG_DIR: Directory paths for input PDFs, output CSV, and log files. These are derived from the project root and typically do not require changes.

Other Runtime Settings:

IN_DEVELOPMENT: Set to True to limit the script to the first 10 pages of each pdf.

BATCH_SIZE: Controls the number of text lines processed in batches (default: 300). Adjust only if encountering memory issues with very large PDFs.

DEBUG_PAGE_RANGE: Limits processing to a specific page range for debugging (e.g., (10, 20) to process only pages 10–20).

PARTY_BY_FILE: A list of party names [] each pdf will have all contests set to one of the party’s in the list. 

SET_FIX_DATE and SET_FIX_BALLOTS_CAST: Allow manual override of event date or total ballots cast if automatic detection fails.

REGULAR_EXPRESSION: Toggles regex-based parsing (currently enabled; disabling is not recommended for standard use).

Important Notes:

After modifying src/config.py, reinstall the package in editable mode to apply changes:

text



pip install -e .
Avoid altering paths unless necessary, as the application automatically creates the output/ and logs/ directories if they do not exist.

 

Acknowledgements
This setup guide was developed with assistance from Grok, an artificial intelligence model built by xAI. Grok provided valuable support in structuring the content, refining language for clarity and professionalism, and ensuring logical flow throughout the document.

clipboard Related articles

Filter by label
There are no items with the selected labels at this time.