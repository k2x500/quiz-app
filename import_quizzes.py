"""
Standalone script to import all quiz data from CSV files into the database.
Run this script to populate or update the quiz database.
"""

from app import app, db, Quiz, Question, import_all_quizzes

if __name__ == '__main__':
    print("\n" + "="*60)
    print("QUIZ DATA IMPORT SCRIPT")
    print("="*60)
    print("\nThis script will:")
    print("  1. Find all CSV files in the csv_files folder")
    print("  2. Import all quiz questions into the database")
    print("  3. Replace existing data with new data from CSVs")
    print("\n" + "="*60 + "\n")
    
    input("Press Enter to start the import process...")
    
    with app.app_context():
        # Ensure database tables exist
        db.create_all()
        
        # Run the import
        stats = import_all_quizzes()
        
        # Final verification
        print("\n" + "="*60)
        print("VERIFICATION")
        print("="*60)
        
        total_quizzes = Quiz.query.count()
        total_questions = Question.query.count()
        
        print(f"\nTotal quizzes in database: {total_quizzes}")
        print(f"Total questions in database: {total_questions}")
        
        print("\nQuizzes by category:")
        categories = db.session.query(Quiz.category).distinct().all()
        for (category,) in categories:
            if category:
                count = Quiz.query.filter_by(category=category).count()
                print(f"  - {category}: {count} quizzes")
        
        print("\n" + "="*60)
        print("IMPORT COMPLETE!")
        print("="*60 + "\n")
        
        print("You can now:")
        print("  • Start the Flask app (python app.py)")
        print("  • Access all imported quizzes in the application")
        print("  • Run this script again to refresh the data\n")

