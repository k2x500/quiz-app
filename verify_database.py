"""
Verification script to confirm all quiz data is correctly imported
"""

from app import app, db, Quiz, Question

if __name__ == '__main__':
    with app.app_context():
        print("\n" + "="*70)
        print("DATABASE VERIFICATION REPORT")
        print("="*70 + "\n")
        
        # Overall stats
        total_quizzes = Quiz.query.count()
        total_questions = Question.query.count()
        
        print(f"OVERALL STATISTICS:")
        print(f"  Total Quizzes: {total_quizzes}")
        print(f"  Total Questions: {total_questions}")
        print(f"  Average Questions per Quiz: {total_questions / total_quizzes:.1f}")
        
        # By category
        print(f"\n{'='*70}")
        print("QUIZZES BY CATEGORY:")
        print("="*70)
        
        categories = db.session.query(Quiz.category).distinct().all()
        for (category,) in categories:
            if category:
                quizzes = Quiz.query.filter_by(category=category).all()
                total_q = sum(len(q.questions) for q in quizzes)
                
                print(f"\n{category} ({len(quizzes)} quizzes, {total_q} questions):")
                for quiz in quizzes:
                    single_answer = sum(1 for q in quiz.questions if ',' not in q.correct_answers)
                    multiple_answer = sum(1 for q in quiz.questions if ',' in q.correct_answers)
                    print(f"  - {quiz.title}: {len(quiz.questions)} questions")
                    print(f"      (Single: {single_answer}, Multiple: {multiple_answer})")
        
        # Check for issues
        print(f"\n{'='*70}")
        print("INTEGRITY CHECKS:")
        print("="*70)
        
        issues = []
        
        # Check for quizzes without questions
        empty_quizzes = Quiz.query.filter(~Quiz.questions.any()).all()
        if empty_quizzes:
            issues.append(f"Found {len(empty_quizzes)} quizzes with no questions")
        else:
            print("  - All quizzes have questions: OK")
        
        # Check for orphaned questions
        orphaned = Question.query.filter(~Question.quiz.has()).count()
        if orphaned > 0:
            issues.append(f"Found {orphaned} orphaned questions")
        else:
            print("  - No orphaned questions: OK")
        
        # Check for questions with missing options
        incomplete = Question.query.filter(
            (Question.option_a == None) | 
            (Question.option_b == None)
        ).count()
        if incomplete > 0:
            issues.append(f"Found {incomplete} questions with missing required options")
        else:
            print("  - All questions have required options: OK")
        
        if issues:
            print(f"\n  ISSUES FOUND:")
            for issue in issues:
                print(f"    ! {issue}")
        else:
            print("\n  ALL CHECKS PASSED!")
        
        print(f"\n{'='*70}")
        print("VERIFICATION COMPLETE")
        print("="*70 + "\n")

