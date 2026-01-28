from app.services.complexity_engine import compute_complexity

easy = """
Define DBMS
• Data
• Information
"""

medium = """
Explain SQL commands
• DDL
• DML
• DCL
"""

hard = """
Analyze normalization techniques
• Functional dependency
• 1NF, 2NF, 3NF
• BCNF
"""

print("Easy topic =>", compute_complexity(easy, 1))
print("Medium topic =>", compute_complexity(medium, 2))
print("Hard topic =>", compute_complexity(hard, 3))
