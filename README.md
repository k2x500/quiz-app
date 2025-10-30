# Quiz Generator

A web-based application that converts .docx files containing quiz questions into interactive online quizzes.

## Features

- Upload .docx files with numbered questions and multiple-choice options
- Automatic parsing and CSV generation
- Interactive quiz with randomized questions and options
- Real-time answer checking
- Score tracking and results summary
- Responsive design that works on desktop and mobile

## Installation

1. Install Python 3.7 or higher
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python app.py
   ```

2. Open your web browser and go to `http://localhost:5000`

3. Upload a .docx file containing quiz questions in the following format:
   - Questions should be numbered (e.g., "1.", "23.")
   - Options should be lettered (a., b., c., d., e.)
   - Correct answers should be written in uppercase letters at the end of each question

## File Format Example

```
11. Which of the following clauses are included in the definition of chronic kidney disease?
a. Glomerular filtration rate < 60 ml/min/1.73m2
b. Kidney damage defined by structural or functional abnormalities of the kidney
c. Age >70 years old
d. Blood urea nitrogen increased
e. The patient is undergoing a renal replacement therapy
ABE
```

## API Endpoints

- `GET /` - Main upload page
- `POST /upload` - Upload and process .docx file
- `GET /download_csv/<filename>` - Download generated CSV file
- `GET /quiz` - Interactive quiz page
- `GET /get_quiz_data` - Get shuffled quiz questions
- `POST /check_answer` - Check user's answer

## Technologies Used

- Python Flask (web framework)
- python-docx (document parsing)
- HTML/CSS/JavaScript (frontend)
- CSV (data format)

## License

This project is open source and available under the MIT License.
