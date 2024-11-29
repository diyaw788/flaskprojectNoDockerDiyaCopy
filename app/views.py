# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Flask modules
from flask   import jsonify, render_template, request, redirect, url_for, flash, session, Flask
from jinja2  import TemplateNotFound
from datetime import datetime
import os
import pandas as pd
import json
# import requests


# App modules
from app import app, cursor, conn
# from app.models import Profiles

# set a global variable for the userID
CURRENT_UID = "1234"
# Upload folder configuration
# Set upload folder path
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

# Create the uploads directory if it does not exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def indexFunction():
    print("entered the index function")
    return redirect(url_for('sign_in'))

@app.route('/create_evals', methods=['GET', 'POST'])
def create_evals():
    from datetime import datetime

    courseOfferingID = request.args.get('courseOfferingID')
    courseName = request.args.get('courseName')
    evaluationName = request.form.get('evaluationName')
    evaluationDescription = request.form.get('evaluationDescription')
    dueDate = request.form.get('dueDate')

    # Get the current date
    assigned_date = datetime.now().date()

    # Validate dueDate
    try:
        dueDate = datetime.strptime(dueDate, '%Y-%m-%d').date()
        if dueDate < assigned_date:
            error_message = "Due date cannot be earlier than the assigned date."
            return render_template('schedule_eval.html', courseOfferingID=courseOfferingID, courseName=courseName, error=error_message)
    except ValueError:
        error_message = "Invalid date format. Please use YYYY-MM-DD."
        return render_template('schedule_eval.html', courseOfferingID=courseOfferingID, courseName=courseName, error=error_message)

    # get all the Group_ID for the course offering ID
    sql = "select * from [peer-eval-db].dbo.CourseGroups where COID = ?"
    cursor.execute(sql, (courseOfferingID,))
    groups = cursor.fetchall()

    # get all the students for each group
    for group in groups:
        student_sql = "select Group_ID, [peer-eval-db].dbo.Student.Student_ID, [peer-eval-db].dbo.Student.Student_Name from [peer-eval-db].dbo.StudentGroups Join [peer-eval-db].dbo.Student on [peer-eval-db].dbo.Student.Student_ID = [peer-eval-db].dbo.StudentGroups.Student_ID where Group_ID = ?"
        cursor.execute(student_sql, (group.Group_ID,))
        students = cursor.fetchall()
        for student_evaluating in students:
            for student_being_evaluated in students:
                if student_evaluating.Student_ID != student_being_evaluated.Student_ID:
                    # schedule an eval between student_evaluating and student_being_evaluated
                    print("###")
                    print('Student Evaluating' + student_evaluating.Student_Name)
                    print('Student Being Evaluated' + student_being_evaluated.Student_Name)
                    evaluation_sql = '''INSERT INTO [peer-eval-db].dbo.Scheduled_Eval (
                            Student_Being_Evaluated_ID,
                            Student_Evaluating_ID,
                            Status,
                            Due_Date,
                            COID,
                            Assigned_Date,
                            Submission_Date,
                            Scheduled_Eval_Name,
                            Scheduled_Eval_Description
                        )
                        VALUES (
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        );

                        '''
                    cursor.execute(evaluation_sql, (
                        student_being_evaluated.Student_ID,
                        student_evaluating.Student_ID,
                        "Incomplete",
                        dueDate,
                        courseOfferingID,
                        assigned_date,
                        None,
                        evaluationName,
                        evaluationDescription
                    ))
                    conn.commit()

    return render_template('schedule_eval.html', courseOfferingID=courseOfferingID, courseName=courseName)


@app.route('/schedule_eval')
def schedule_eval():
    courseOfferingID = request.args.get('courseOfferingID')
    courseName = request.args.get('courseName')
    return render_template('schedule_eval.html', courseOfferingID=courseOfferingID, courseName=courseName)

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    # POST when sign in being submitted
    if request.method == 'POST':

        # get form contents
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        try:
            # Query the database for the user with the provided email and password based on their role
            if role == 'professor':
                sql = "SELECT * FROM Professor WHERE Professor_Email = ? AND Password = ?"
            elif role == 'student':
                sql = "SELECT * FROM Student WHERE Email = ? AND Password = ?"

            cursor.execute(sql, (email, password))
            user = cursor.fetchone()

            print("this is the user:", user)

            # if user holds a value, then a user with that info was found
            if user:
                user_dict = {
                    'ID': int(user[0]),           # Ensure ID is an integer
                    'Name': str(user[1]),         # Ensure Name is a string
                    'Email': str(user[2]),        # Ensure Email is a string
                    'Password': str(user[3]),     # Ensure Password is a string
                    'Role': str(role)             # Ensure Role is a string
                }
                print(user_dict)

                # Store user information in session
                session['user'] = user_dict

                # Render the correct page based on who is signing in
                user_role = session['user'].get('Role')
                if user_role == 'professor':
                    # return render_template('professor_home.html', user=user_dict)
                    return redirect(url_for('professor_home'))
                elif user_role == 'student':
                    # return render_template('student_home.html', user=user_dict)
                    return redirect(url_for('student_home'))
            else:
                flash('Incorrect email, password, or role. Please try again.', 'error')
                return redirect(url_for('sign_in'))
        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred: {}'.format(str(e)), 'error')
            return redirect(url_for('sign_in'))
    # GET when page just being loaded 
    else:
        return render_template('sign_in.html')
    
@app.route('/professor_home', methods=['GET', 'POST'])
def professor_home():
    return render_template('professor_home.html')
    
@app.route('/get_courses', methods = ['GET']) 
def get_courses():
    print("just entered get courses")
    try:
        user = session.get('user')
        professorID = user.get('ID')
        professorName = user.get('Name')
        print(user)

        sql = '''
            SELECT [peer-eval-db].dbo.CourseOfferings.COID, Semester, Year, Section, Course_Name FROM [peer-eval-db].dbo.ProfessorCourse 
            JOIN [peer-eval-db].dbo.CourseOfferings ON [peer-eval-db].dbo.ProfessorCourse.COID=[peer-eval-db].dbo.CourseOfferings.COID
            JOIN [peer-eval-db].dbo.Courses ON [peer-eval-db].dbo.Courses.Course_ID=[peer-eval-db].dbo.CourseOfferings.Course_ID
            WHERE Professor_ID = ?;
        '''
        cursor.execute(sql, (professorID,))

        courses = cursor.fetchall()
        print("these are the courses")
        print(courses)
        # (1, 'Fall', 2024, 'A', 'Financial Accounting')
        courses = [
            {
                "COID": row[0],
                "Semester": row[1],
                "Year": row[2],
                "Section": row[3],
                "Course_Name": row[4]
            }
            for row in courses
        ]
        print("i reach here")
        return jsonify(courses)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/log_out', methods=['GET', 'POST'])
def log_out():
    session.clear()
    print("printing if there is a user still")
    print(session.get('user'))
    return redirect(url_for('sign_in'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            try:
                # Read the CSV file and strip whitespace from column headers
                data = pd.read_csv(filepath, encoding='utf-8')
                data.columns = data.columns.str.strip().str.lower()  # Remove whitespace and convert to lowercase
                print("Columns in CSV file:", data.columns.tolist())  # Debugging: Print columns to verify

                # Define required columns and expected data types
                required_columns = {'student_id', 'student_name', 'coid', 'group_id'}
                
                # Check if all required columns are present
                if not required_columns.issubset(data.columns):
                    missing_columns = required_columns - set(data.columns)
                    flash(f'Missing columns in the file: {", ".join(missing_columns)}')
                    return redirect(request.url)

                # Validate each row for completeness and correct data types
                for index, row in data.iterrows():
                    # Check for missing values
                    if pd.isnull(row['student_id']) or pd.isnull(row['student_name']) or pd.isnull(row['coid']) or pd.isnull(row['group_id']):
                        flash(f'Row {index + 1} has missing values.')
                        return redirect(request.url)

                    # Check data types
                    try:
                        student_id = row['student_id']
                        print(student_id)
                        student_id = str(row['student_id'])
                        print("this is the string student id" + student_id)
                        student_name = str(row['student_name'])
                        coid = int(row['coid'])
                        group_id = int(row['group_id'])
                    except ValueError as e:
                        flash(f'Row {index + 1} has incorrect data types: {e}')
                        return redirect(request.url)

                    # Insert row into the database if all checks pass
                    try:
                        cursor.execute("SELECT * FROM Student WHERE Student_ID = ?", (student_id,))
                        student = cursor.fetchone()
                        if student:
                            flash(f'Student in Row {index + 1} already exists in the system')
                            # if the student already exists but is being added into a new course
                            # cursor.execute("SELECT * FROM StudentCourses WHERE Student_ID = ? AND COID = ?", (student_id, coid))
                            # course = cursor.fetchone()
                            # if !course:
                        else:
                            # Construct the SQL query with the parameters manually injected for printing
                            query = f"""
                                INSERT INTO dbo.Student (Student_ID, Student_Name, Email, Password)
                                VALUES ({student_id}, '{student_name}', '{student_id}', 'x');
                            """
                            # Print the query to see the final format
                            print("Executing query:", query)

                            # Execute the query using a parameterized approach to prevent SQL injection
                            cursor.execute("""
                                INSERT INTO dbo.Student (Student_ID, Student_Name, Email, Password)
                                VALUES (?, ?, ?, 'x');
                            """, (student_id, student_name, str(student_id)))


                            cursor.execute("""
                                INSERT INTO dbo.StudentCourses (Student_ID, COID)
                                VALUES (?, ?);
                            """, (student_id, coid))
    
                            if group_id != 0:
                                cursor.execute("""
                                    INSERT INTO dbo.StudentGroups (Group_ID, Student_ID, Student_Name)
                                    VALUES (?, ?, ?);
                                """, (group_id, student_id, student_name))
                            conn.commit()
                    except Exception as e:
                        print(f"Error inserting row {index}: {e}")

                flash('File uploaded and processed successfully!')
            except Exception as e:
                flash(f'Error processing file: {e}')
            
            return redirect(url_for('upload_file'))
        
        flash('File type is not allowed. Please upload a CSV file.')
        return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/view_course_students/<int:courseOfferingID>/<string:courseName>')
def view_course_students(courseOfferingID, courseName):
    try:
        # Fetch all groups associated with the course
        cursor.execute("""
            SELECT g.Group_ID, g.Group_Name
            FROM Groups g
            JOIN CourseGroups cg ON g.Group_ID = cg.Group_ID
            WHERE cg.COID = ?
        """, (courseOfferingID,))
        groups = [{'Group_ID': row[0], 'Group_Name': row[1]} for row in cursor.fetchall()]
        
        # Add an "Unassigned" group to the list
        groups.append({'Group_ID': -1, 'Group_Name': 'Unassigned'})
        groups.append({'Group_ID': -2, 'Group_Name': 'All Groups'})

        # Fetch students and convert rows to dictionaries
        query = '''Select Student.Student_ID, Student.Student_Name, Groups.Group_ID, Groups.Group_Name from StudentCourses
                join Student on Student.Student_ID = StudentCourses.Student_ID
                join StudentGroups on StudentCourses.Student_ID = StudentGroups.Student_ID
                join Groups on StudentGroups.Group_ID = Groups.Group_ID
                where COID = ?;'''
        cursor.execute(query, (courseOfferingID,))
        students = [{'Student_ID': row[0], 'Student_Name': row[1], 'Group_ID': row[2], 'Group_Name': row[3]} for row in cursor.fetchall()]
        print(students)
        
    except Exception as e:
        print(f"Error fetching students: {e}")
        groups = []
        students = []
    
    return render_template('professor_dashboard.html', courseOfferingID=courseOfferingID, courseName=courseName, groups=groups, students=students)

@app.route('/addstudent1', methods=['GET'])
def add_student1():
    print("registering the click of add student")
    courseOfferingID = request.args.get('courseOfferingID')
    courseName = request.args.get('courseName')
    # groups = request.args.get('groups')
    try:
        # Query the CourseGroups table to get all groups for the specific courseOfferingID
        query = '''SELECT * FROM CourseGroups 
                JOIN Groups ON CourseGroups.Group_ID = Groups.Group_ID
                WHERE COID = ?'''
        cursor.execute(query, (courseOfferingID,))
        
        # Fetch all matching records
        groups = cursor.fetchall()
        print(groups)
        # Optional: Process the result to convert it into a more usable format (e.g., list of dictionaries)
        group_list = []
        for group in groups:
            group_data = {
                'GroupID': group.Group_ID,
                'CourseOfferingID': group.COID,
                'GroupName': group.Group_Name,
                # Add any other relevant fields
            }
            group_list.append(group_data)
            print(group_list)

    except Exception as e:
        print(f"Error fetching groups: {e}")
        flash("An error occurred while fetching groups.")
        group_list = []

    return render_template('addstudent1.html', groups=group_list, courseOfferingID=courseOfferingID, courseName=courseName)

@app.route('/get_group_students', methods=['GET'])
def get_group_students():
    groupID = request.args.get('groupID')
    courseOfferingID = request.args.get('courseOfferingID')

    try:
        if groupID == 'None':  # Fetch students not assigned to any group within the course
            cursor.execute("""
                SELECT s.Student_Name, s.Student_ID, NULL as Group_ID
                FROM Student s
                LEFT JOIN StudentGroups sg ON s.Student_ID = sg.Student_ID
                LEFT JOIN CourseStudents cs ON s.Student_ID = cs.Student_ID
                WHERE sg.Group_ID IS NULL AND cs.COID = ?
            """, (courseOfferingID,))
        else:
            if groupID == '-2':
                print("okay, this is where were supposed to print all students")
                print(courseOfferingID)
                cursor.execute('''Select Student.Student_Name, Student.Student_ID, Groups.Group_ID, Groups.Group_Name from StudentCourses
                    join Student on Student.Student_ID = StudentCourses.Student_ID
                    join StudentGroups on StudentCourses.Student_ID = StudentGroups.Student_ID
                    join Groups on StudentGroups.Group_ID = Groups.Group_ID
                    where COID = ?;''', (courseOfferingID,))
            else:
                cursor.execute("""
                    SELECT s.Student_Name, s.Student_ID, sg.Group_ID, g.Group_Name
                    FROM Student s
                    JOIN StudentGroups sg ON s.Student_ID = sg.Student_ID
                    JOIN Groups g ON sg.Group_ID = g.Group_ID
                    WHERE sg.Group_ID = ?
                """, (groupID,))
        
        students = [{'Student_Name': row[0], 'Student_ID': row[1], 'Group_ID': row[2], 'Group_Name': row[3]} for row in cursor.fetchall()]
        print("hi DIYa PLEASE look here")
        print(students)
        if not students:
            return jsonify({'error': 'No students found for this group'}), 404

        return jsonify(students)
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

# @app.route('/get_all_students', methods=['GET'])
# def get_all_students(courseOfferingID, courseName):
#     try:
#         # get all students in a specific course
#         query = "SELECT * FROM StudentCourses WHERE COID = ?"
#         cursor.execute(query, (courseOfferingID,))
        
#         students = cursor.fetchall()
#         print(students)

#         # # Optional: Process the result to convert it into a more usable format (e.g., list of dictionaries)
#         # group_list = []
#         # for group in groups:
#         #     group_data = {
#         #         'GroupID': group.Group_ID,
#         #         'CourseOfferingID': group.COID
#         #         # Add any other relevant fields
#         #     }
#         #     group_list.append(group_data)
#         #     print(group_list)

#     except Exception as e:
#         print(f"Error fetching groups: {e}")
#         flash("An error occurred while fetching groups.")
#         group_list = []

#     return render_template('professor_dashboard.html', groups=group_list, courseOfferingID=courseOfferingID, courseName=courseName, students=students)

# @app.route('/successPage')
# def successPage():
#     return render_template('successPage.html')

@app.route('/diyas_submit_student', methods=['POST'])
def diyas_submit_student():
    print("DIYA PLEASE")
    courseOfferingID = request.args.get('courseOfferingID')
    courseName = request.args.get('courseName')
    groups = request.args.get('groups')
    student_id = request.form['student_id']
    name = request.form['name']
    groupSelect = request.form['groupSelect']
    cursor.execute("""
                        INSERT INTO dbo.Student (Student_ID, Student_Name, Email, Password)
                        VALUES (?, ?, ?, 'x');
                    """, (student_id, name, str(student_id)))
    conn.commit()

    cursor.execute("""
                        INSERT INTO dbo.StudentCourses (Student_ID, COID)
                        VALUES (?, ?);
                    """, (student_id, courseOfferingID))
    conn.commit()

    if groupSelect != "Unassigned":
        cursor.execute("""
                            INSERT INTO dbo.StudentGroups (Group_ID, Student_ID, Student_Name)
                            VALUES (?, ?, ?);
                        """, (groupSelect, student_id, name))
        conn.commit()
    # return render_template('successPage.html')
    query = '''SELECT * FROM [peer-eval-db].dbo.CourseGroups 
            join [peer-eval-db].dbo.Groups on CourseGroups.Group_ID = Groups.Group_ID
            WHERE COID = ?'''
    
    cursor.execute(query, (courseOfferingID,))
    print("diya here today")
    # groups
    groups = cursor.fetchall()
    group_list = []
    for group in groups:
        group_data = {
            'Group_ID': group.Group_ID,
            'CourseOfferingID': group.COID,
            'Group_Name': group.Group_Name
            # Add any other relevant fields
        }
        group_list.append(group_data)
    print("hi diya, here is a list of the groups: ")
    print(groups)

    print("DIYA HELP ME")
    # Fetch students and convert rows to dictionaries
    query = '''Select Student.Student_ID, Student.Student_Name, Groups.Group_ID, Groups.Group_Name from StudentCourses
            join Student on Student.Student_ID = StudentCourses.Student_ID
            join StudentGroups on StudentCourses.Student_ID = StudentGroups.Student_ID
            join Groups on StudentGroups.Group_ID = Groups.Group_ID
            where COID = ?;'''
    cursor.execute(query, (courseOfferingID,))
    students = [{'Student_ID': row[0], 'Student_Name': row[1], 'Group_ID': row[2], 'Group_Name': row[3]} for row in cursor.fetchall()]
        
    return redirect(url_for('view_course_students', courseOfferingID=courseOfferingID, courseName=courseName))

    # return render_template('professor_dashboard.html', courseOfferingID=courseOfferingID, courseName=courseName, groups=groups)
    # return render_template('professor_dashboard.html', courseOfferingID=courseOfferingID, courseName=courseName, groups=groups, students=students)



# @app.route('/viewCourseStudents/<int:courseOfferingID>/<string:courseName>')
# def viewCourseStudents(courseOfferingID, courseName):
#     try:
#         # Fetch all groups associated with the course
#         cursor.execute("""
#             SELECT g.Group_ID, g.Group_Name
#             FROM Groups g
#             JOIN CourseGroups cg ON g.Group_ID = cg.Group_ID
#             WHERE cg.COID = ?
#         """, (courseOfferingID,))
#         groups = [{'Group_ID': row[0], 'Group_Name': row[1]} for row in cursor.fetchall()]
        
#         # Add an "Unassigned" group to the list
#         groups.append({'Group_ID': -1, 'Group_Name': 'Unassigned'})
        
#     except Exception as e:
#         groups = []
#     return render_template('professor_dashboard.html', courseOfferingID=courseOfferingID, courseName=courseName, groups=groups)


# # @app.route('/viewCourseStudents/<int:courseOfferingID>/<string:courseName>')
# # def viewCourseStudents(courseOfferingID, courseName):
# #     try:
# #         cursor.execute("""
# #             SELECT g.Group_ID, g.Group_Name
# #             FROM Groups g
# #             JOIN CourseGroups cg ON g.Group_ID = cg.Group_ID
# #             WHERE cg.COID = ?
# #         """, (courseOfferingID,))
# #         groups = [{'Group_ID': row[0], 'Group_Name': row[1]} for row in cursor.fetchall()]
# #     except Exception as e:
# #         groups = []
# #     return render_template('professor_dashboard.html', courseOfferingID=courseOfferingID, courseName=courseName, groups=groups)

# # @app.route('/viewCourseStudents/<int:courseOfferingID>/<string:courseName>')
# # def viewCourseStudents(courseOfferingID, courseName):
# #     # Use courseID and courseName as needed
# #     # return render_template('success.html')
# #     return render_template('professor_dashboard.html', courseOfferingID=courseOfferingID, courseName=courseName)

# @app.route('/professor_dashboard')
# def professor_dashboard():
#     try:
#         # Assuming CURRENT_UID is the logged-in professor's ID

#         # Fetch course names for the professor
#         cursor.execute("""
#             SELECT c.Course_Name
#             FROM Courses c
#             JOIN CourseOfferings co ON c.Course_ID = co.Course_ID
#             JOIN ProfessorCourse pc ON co.COID = pc.ProfessorCourse_ID
#             WHERE pc.Professor_ID = ?
#         """, (CURRENT_UID,))
#         class_name_row = cursor.fetchone()
#         if class_name_row:
#             class_name = class_name_row[0]
#             app.logger.info(f"Class Name: {class_name}")
#         else:
#             class_name = "No courses found"
#             app.logger.info("No courses found for the given professor ID")

#         # Fetch group names for the courses taught by the professor
#         cursor.execute("""
#             SELECT g.Group_Name
#             FROM Groups g
#             JOIN CourseGroups cg ON g.Group_ID = cg.Group_ID
#             JOIN CourseOfferings co ON cg.Course_ID = co.Course_ID
#             JOIN ProfessorCourse pc ON co.COID = pc.ProfessorCourse_ID
#             WHERE pc.Professor_ID = ?
#         """, (CURRENT_UID,))
#         groups = [row[0] for row in cursor.fetchall()]
#         app.logger.info(f"Groups: {groups}")

#         return render_template('professor_dashboard.html', class_name=class_name, groups=groups)
#     except Exception as e:
#         app.logger.error(f"An error occurred: {e}")
#         return f"An error occurred: {e}", 500


# # @app.route('/get_group_students', methods=['GET'])
# # def get_group_students():
# #     groupID = request.args.get('groupID')
# #     if not groupID:
# #         return jsonify({'error': 'No group ID provided'}), 400

# #     try:
# #         cursor.execute("""
# #             SELECT s.Student_Name, sg.Group_ID
# #             FROM Student s
# #             JOIN StudentGroups sg ON s.Student_ID = sg.Student_ID
# #             WHERE sg.Group_ID = ?
# #         """, (groupID,))
# #         students = [{'Student_Name': row[0], 'Group_ID': row[1]} for row in cursor.fetchall()]

# #         if not students:
# #             return jsonify({'error': 'No students found for this group'}), 404

# #         return jsonify(students)
# #     except Exception as e:
# #         return jsonify({'error': f'Internal server error: {str(e)}'}), 500

# if __name__ == "__main__":
#     app.run(debug=True)

# @app.route('/get_group_data')
# def get_group_data():
#     print("we reached here get group data")
#     courseOfferingID = request.args.get('group')
#     try:
#         sql = '''
#             SELECT dbo.StudentCourses.Student_ID, Student_Name 
#             FROM dbo.StudentCourses 
#             JOIN dbo.Student ON dbo.StudentCourses.Student_ID = dbo.Student.Student_ID 
#             WHERE COID = ?;
#         '''
#         cursor.execute(sql, (courseOfferingID,))
#         students = cursor.fetchall()
#         print(students)
#         student_data = [{'student': row[1], 'group': row[0]} for row in students]
#         return jsonify(student_data)
#     except Exception as e:
#         print("Error:", str(e))
#         return jsonify({"error": str(e)}), 500



# @app.route('/get_group_data1')
# def get_group_data1():
#     courseOfferingID = request.args.get('group')
#     try:
#         sql = '''
#             SELECT dbo.CourseGroups.Group_ID, dbo.Groups.Group_Name 
#             FROM dbo.CourseGroups 
#             JOIN dbo.CourseOfferings ON dbo.CourseGroups.COID = dbo.CourseOfferings.COID
#             JOIN dbo.Courses ON dbo.Courses.Course_ID = dbo.CourseOfferings.Course_ID 
#             JOIN dbo.Groups ON dbo.CourseGroups.Group_ID = dbo.Groups.Group_ID 
#             WHERE dbo.CourseGroups.COID = ?;
#         '''
#         cursor.execute(sql, (courseOfferingID,))
#         groups = cursor.fetchall()
#         print(groups)
#         group_data = [{'group_id': row[0], 'group_name': row[1]} for row in groups]
#         return jsonify(group_data)
#     except Exception as e:
#         print("Error:", str(e))
#         return jsonify({"error": str(e)}), 500


# # @app.route('/get_group_data')
# # def get_group_data():
# #     group = request.args.get('group')
# #     try:
# #         if group == "Unassigned":
# #             cursor.execute("""
# #                 SELECT s.Student_Name, 'Unassigned' AS Group_Name
# #                 FROM Students s
# #                 LEFT JOIN StudentGroups sg ON s.Student_ID = sg.Student_ID
# #                 LEFT JOIN Groups g ON sg.Group_ID = g.Group_ID
# #                 LEFT JOIN CourseOfferings co ON s.COID = co.COID
# #                 JOIN ProfessorCourse pc ON co.COID = pc.COID
# #                 WHERE sg.Group_ID IS NULL AND pc.Professor_ID = ?
# #             """, (CURRENT_UID,))
# #         else:
# #             cursor.execute("""
# #                 SELECT s.Student_Name, g.Group_Name
# #                 FROM Students s
# #                 JOIN StudentGroups sg ON s.Student_ID = sg.Student_ID
# #                 JOIN Groups g ON sg.Group_ID = g.Group_ID
# #                 LEFT JOIN CourseOfferings co ON s.COID = co.COID
# #                 JOIN ProfessorCourse pc ON co.COID = pc.COID
# #                 WHERE g.Group_Name = ? AND pc.Professor_ID = ?
# #             """, (group, CURRENT_UID))
        
# #         students = cursor.fetchall()
# #         student_data = [{'student': row[0], 'group': row[1]} for row in students]
# #         return jsonify(student_data)
# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500


# @app.route('/assign_group', methods=['POST'])
# def assign_group():
#     data = request.json
#     try:
#         for assignment in data['assignments']:
#             student_name, group_name = assignment.split('|')
#             cursor.execute("""
#                 UPDATE StudentGroups
#                 SET Group_ID = (SELECT Group_ID FROM Groups WHERE Group_Name = ?)
#                 FROM StudentGroups sg
#                 JOIN Student s ON sg.Student_ID = s.Student_ID
#                 WHERE s.Student_Name = ?
#             """, (group_name, student_name))
#         conn.commit()
#         return jsonify({"success": True})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
    
# @app.route('/addstudent')
# def add_student():
#     courseOfferingID = request.args.get('courseOfferingID')
#     courseName = request.args.get('courseName')
#     return render_template('addstudent.html', courseOfferingID=courseOfferingID, courseName=courseName)

# # @app.route('/addstudent')
# # def add_student():
# #     courseOfferingID = request.args.get('courseOfferingID')
# #     courseName = request.args.get('courseName')
# #     return render_template('addstudent.html', courseOfferingID=courseOfferingID, courseName=courseName)

# # @app.route('/addstudent')
# # def add_student():
# #     return render_template('addstudent.html')

# # @app.route('/submit_student', methods=['POST'])
# # def submit_student():
# #     student_id = request.form['student_id']
# #     name = request.form['name']
# #     email = request.form['email']
# #     password = request.form['password']
# #     try:
# #         cursor.execute("""
# #             INSERT INTO Student (Student_ID, Student_Name, Email, Password)
# #             VALUES (?, ?, ?, ?)
# #         """, (student_id, name, email, password))
# #         conn.commit()
# #         return redirect(url_for('professor_dashboard'))
# #     except Exception as e:
# #         return f"An error occurred: {e}", 500
# # @app.route('/submit_student', methods=['POST'])
# # def submit_student():
# #     student_id = request.form['student_id']
# #     name = request.form['name']
# #     email = request.form['email']
# #     password = request.form['password']
# #     courseOfferingID = request.args.get('courseOfferingID', type=int)
# #     courseName = request.args.get('courseName')
    
# #     try:
# #         # Check for duplicate Student_ID
# #         cursor.execute("SELECT COUNT(*) FROM Student WHERE Student_ID = ?", (student_id,))
# #         count = cursor.fetchone()[0]
# #         if count > 0:
# #             return f"An error occurred: Duplicate Student_ID {student_id}", 400

# #         cursor.execute("""
# #             INSERT INTO Student (Student_ID, Student_Name, Email, Password)
# #             VALUES (?, ?, ?, ?)
# #         """, (student_id, name, email, password))
# #         conn.commit()
        
# #         return redirect(url_for('viewCourseStudents', courseOfferingID=courseOfferingID, courseName=courseName))
# #     except Exception as e:
# #         return f"An error occurred: {e}", 500

# @app.route('/submit_student', methods=['POST'])
# def submit_student():
#     student_id = request.form['student_id']
#     name = request.form['name']
#     email = request.form['email']
#     password = request.form['password']
#     courseOfferingID = request.args.get('courseOfferingID', type=int)
#     courseName = request.args.get('courseName')
    
#     try:
#         # Check for duplicate Student_ID
#         cursor.execute("SELECT COUNT(*) FROM Student WHERE Student_ID = ?", (student_id,))
#         count = cursor.fetchone()[0]
#         if count > 0:
#             return f"An error occurred: Duplicate Student_ID {student_id}", 400

#         cursor.execute("""
#             INSERT INTO Student (Student_ID, Student_Name, Email, Password)
#             VALUES (?, ?, ?, ?)
#         """, (student_id, name, email, password))
#         conn.commit()
        
#         return redirect(url_for('viewCourseStudents', courseOfferingID=courseOfferingID, courseName=courseName))
#     except Exception as e:
#         return f"An error occurred: {e}", 500

# @app.route('/edit_student/<int:studentID>')
# def edit_student(studentID):
#     courseOfferingID = request.args.get('courseOfferingID')
#     courseName = request.args.get('courseName')
#     try:
#         cursor.execute("SELECT Student_ID, Student_Name, Email, Password FROM Student WHERE Student_ID = ?", (studentID,))
#         student = cursor.fetchone()
#         if student:
#             student_data = {
#                 'Student_ID': student[0],
#                 'Student_Name': student[1],
#                 'Email': student[2],
#                 'Password': student[3]
#             }
#             return render_template('editstudent.html', student=student_data, courseOfferingID=courseOfferingID, courseName=courseName)
#         else:
#             return "Student not found", 404
#     except Exception as e:
#         return f"An error occurred: {e}", 500
# # @app.route('/editstudent')
# # def edit_student():
# #     student_id = request.args.get('student_id')
# #     cursor.execute("SELECT Student_ID, Student_Name, Email, Password FROM Student WHERE Student_ID = ?", (student_id,))
# #     student = cursor.fetchone()
# #     if student:
# #         student_data = {
# #             'student_id': student[0],
# #             'name': student[1],
# #             'email': student[2],
# #             'password': student[3]
# #         }
# #         return render_template('editstudent.html', student=student_data)
# #     else:
# #         return "Student not found", 404

# @app.route('/update_student/<int:studentID>', methods=['POST'])
# def update_student(studentID):
#     name = request.form['name']
#     email = request.form['email']
#     password = request.form['password']
#     courseOfferingID = request.args.get('courseOfferingID')
#     courseName = request.args.get('courseName')
    
#     try:
#         cursor.execute("""
#             UPDATE Student
#             SET Student_Name = ?, Email = ?, Password = ?
#             WHERE Student_ID = ?
#         """, (name, email, password, studentID))
#         conn.commit()
        
#         return redirect(url_for('viewCourseStudents', courseOfferingID=courseOfferingID, courseName=courseName))
#     except Exception as e:
#         return f"An error occurred: {e}", 500

# # @app.route('/updatestudent', methods=['POST'])
# # def update_student():
# #     student_id = request.form['student_id']
# #     name = request.form['name']
# #     email = request.form['email']
# #     password = request.form['password']
# #     try:
# #         cursor.execute("""
# #             UPDATE Student SET Student_Name = ?, Email = ?, Password = ?
# #             WHERE Student_ID = ?
# #         """, (name, email, password, student_id))
# #         conn.commit()
# #         return redirect(url_for('professor_dashboard'))
# #     except Exception as e:
# #         return f"An error occurred: {e}", 500

@app.route('/change_student_group', methods=['POST'])
def change_student_group():
    studentID = request.args.get('studentID', type=int)
    groupID = request.args.get('groupID')
    
    try:
        if groupID == 'None' or groupID is None:  # Handle unassigned group
            # Delete the student's group assignment, effectively unassigning them
            cursor.execute("""
                DELETE FROM StudentGroups
                WHERE Student_ID = ?
            """, (studentID,))
        else:
            # Check if the student is already in the target group
            cursor.execute("""
                SELECT COUNT(*) 
                FROM StudentGroups
                WHERE Student_ID = ? AND Group_ID = ?
            """, (studentID, groupID))
            count = cursor.fetchone()[0]
            
            if count > 0:
                return jsonify({"error": "Student is already in the selected group."}), 400

            # # Delete the old entry
            # cursor.execute("""
            #     DELETE FROM StudentGroups
            #     WHERE Student_ID = ?
            # """, (studentID,))
            
            # # Insert the new entry
            # cursor.execute("""
            #     INSERT INTO StudentGroups (Student_ID, Group_ID)
            #     VALUES (?, ?)
            # """, (studentID, groupID))

            cursor.execute("""
                UPDATE StudentGroups
                SET Group_ID = ?
                WHERE Student_ID = ?
            """, (groupID, studentID))

        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/remove_student_group', methods=['POST'])
def remove_student_group():
    studentID = request.args.get('studentID', type=int)
    
    try:
        # Delete the student's group assignment, effectively unassigning them
        cursor.execute("""
            DELETE FROM StudentGroups
            WHERE Student_ID = ?
        """, (studentID,))

        cursor.execute("""
            DELETE FROM StudentCourses
            WHERE Student_ID = ?
        """, (studentID,))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/remove_student_class', methods=['POST'])
def remove_student_class():
    studentID = request.args.get('studentID', type=int)
    
    try:
        # Delete the student's group assignment, effectively unassigning them
        cursor.execute("""
            DELETE FROM StudentGroups
            WHERE Student_ID = ?
        """, (studentID,))

        cursor.execute("""
            DELETE FROM StudentCourses
            WHERE Student_ID = ?
        """, (studentID,))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# @app.route('/deletestudent', methods=['DELETE'])
# def delete_student():
#     student_id = request.args.get('student_id')
#     try:
#         cursor.execute("DELETE FROM Student WHERE Student_ID = ?", (student_id,))
#         conn.commit()
#         return jsonify({"success": True})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
    


# @app.route('/sign_in', methods=['GET', 'POST'])
# def sign_in():
#     print("entering the sign in route at all.")
#     if request.method == 'POST':
#         print("entering the sign_in post")
#         email = request.form.get('email')
#         password = request.form.get('password')
#         role = request.form.get('role')

#         try:
#             if role == 'professor':
#                 sql = "SELECT * FROM Professor WHERE Professor_Email = ? AND Password = ?"
#             elif role == 'student':
#                 sql = "SELECT * FROM Student WHERE Email = ? AND Password = ?"

#             # Query the database for the user with the provided email and password
#             cursor.execute(sql, (email, password))
#             user = cursor.fetchone()
#             print("this is the user:", user)
#             if user:
#                 # Convert the Row object to a dictionary
#                 user_dict = {
#                     'ID': int(user[0]),           # Ensure ID is an integer
#                     'Name': str(user[1]),         # Ensure Name is a string
#                     'Email': str(user[2]),        # Ensure Email is a string
#                     'Password': str(user[3]),     # Ensure Password is a string
#                     'Role': str(role)             # Ensure Role is a string
#                 }
#                 print(user_dict)
#                 # Store user information in session
#                 session['user'] = user_dict

#                 user_role = session['user'].get('Role')
#                 if user_role == 'professor':
#                     return render_template('professor_home.html', user=user_dict)
#                 elif user_role == 'student':
#                     return render_template('student_home.html', user=user)
#             else:
#                 flash('Incorrect email or password. Please try again.', 'error')
#                 return redirect(url_for('sign_in'))
#         except Exception as e:
#             print(f"Error: {e}")
#             flash('An error occurred: {}'.format(str(e)), 'error')
#             return redirect(url_for('sign_in'))
#     else:
#         print("entering the signin but not posting")
#         return render_template('sign_in.html')


    
@app.route('/student_home', methods=['GET', 'POST'])
def student_home():
    return render_template('student_home.html')

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        print(name) 
        # Diya Wadhera
        print("this is the role:", role)
        # professor
        
        if role == 'professor':
            # Check if the professor already exists in the database
            cursor.execute('SELECT COUNT(*) FROM Professor WHERE Professor_Email = ?', (email,))
            professor_exists = cursor.fetchone()[0]

            if professor_exists > 0:
                # Professor with this email already exists
                flash('A professor with this email already exists. Please use a different email.', 'error')
                return render_template('sign_up.html')  # Reload the sign-up form with an alert
            else:
                # Insert the new professor record
                cursor.execute('SELECT MAX(Professor_ID) FROM Professor')
                max_id = cursor.fetchone()[0]
                if max_id is None:
                    max_id = 0
                new_id = max_id + 1

                sql = '''
                        INSERT INTO Professor (Professor_ID, Professor_Name, Professor_Email, Password)
                        VALUES (?, ?, ?, ?)
                    '''
                cursor.execute(sql, (new_id, name, email, password))
                conn.commit()
        elif role == 'student':
            student_id = request.form.get('student_id')

            # Check if the student_id exists in the database
            cursor.execute('SELECT Password FROM Student WHERE Student_ID = ?', (student_id,))
            student_record = cursor.fetchone()

            if student_record:
                # Scenario 1 & 2: Student ID exists
                existing_password = student_record[0]

                if existing_password == 'x':
                    # Scenario 1: Update Email and Password
                    cursor.execute('''
                        UPDATE Student
                        SET Email = ?, Password = ?
                        WHERE Student_ID = ?
                    ''', (email, password, student_id))
                    conn.commit()
                    flash('Your account has been successfully updated.', 'success')
                else:
                    # Scenario 2: Account already exists
                    flash('An account already exists for this Student ID.', 'error')
                    return render_template('sign_up.html')  # Reload the form
            else:
                # Scenario 3: Insert a new student record
                cursor.execute('''
                    INSERT INTO Student (Student_ID, Student_Name, Email, Password)
                    VALUES (?, ?, ?, ?)
                ''', (student_id, name, email, password))
                conn.commit()
                flash('Your account has been successfully created.', 'success')

        return render_template('sign_in.html')
    else:
        return render_template('sign_up.html')


# @app.route('/studentLogin', methods=['GET', 'POST'])

# def studentLogin():

#     if request.method == 'POST':

#         email = request.form['email']

#         password = request.form['password']

 

#         try:

#             # Query the database for the user with the provided email and password

#             sql = "SELECT * FROM Student WHERE Email = ? AND Password = ?"

#             cursor.execute(sql, (email, password))

#             user = cursor.fetchone()

       

#             if user:

#                 # Convert the Row object to a dictionary

#                 user_dict = {

#                     'id': user[0],

#                     'name': user[1],

#                     'email': user[2],

#                     'password': user[3]

#                 }

#                 # Store user information in session

#                 session['user'] = user_dict

#                 print("User session set:", session['user'])

#                 flash('Login successful!', 'success')

#                 return redirect(url_for('index'))

#             else:

#                 flash('Incorrect email or password. Please try again.', 'error')

#                 return redirect(url_for('studentLogin'))

#         except Exception as e:

#             print(f"Error: {e}")

#             flash('An error occurred: {}'.format(str(e)), 'error')

#             return redirect(url_for('studentLogin'))

 

#     return render_template('studentLogin.html')

# @app.route('/success')
# def success():
#     return render_template('success.html')

# @app.route('/index')
# def index():
#     return render_template('index.html')

# # @app.route('/test2/<string:beingEval>/<string:evaluatorName>')
# # def test2(beingEval, evaluatorName):
# #     return render_template('test2.html', beingEval=beingEval, evaluatorName=evaluatorName)
 

@app.route('/get_evaluations', methods = ['GET']) 
def get_evaluations():
    try:
        evaluatorName = request.args.get("evaluatorName")
        evaluatorID = request.args.get("evaluatorID")

        print(evaluatorName, " ", evaluatorID)
        # sql = "select SID_BeingEval, SID_Evaluating, Status, Due_Date from Scheduled_Eval where SID_Evaluating = ?"
        cursor.execute('''SELECT 
                            s1.Student_Name AS Student_Being_Evaluated_Name,
                            s2.Student_Name AS Student_Evaluating_Name,
                            se.Status,
                            se.Due_Date, 
                            se.Scheduled_Eval_Name
                        FROM [peer-eval-db].dbo.Scheduled_Eval AS se
                        LEFT JOIN [peer-eval-db].dbo.Student AS s1
                            ON se.Student_Being_Evaluated_ID = s1.Student_ID
                        LEFT JOIN [peer-eval-db].dbo.Student AS s2
                            ON se.Student_Evaluating_ID = s2.Student_ID
                        WHERE se.Student_Evaluating_ID = ?;
                        ''', evaluatorID)
        evaluations = cursor.fetchall()
        print(evaluations)
        evaluations = [
            {"Student_Being_Evaluated_Name": row.Student_Being_Evaluated_Name, "Student_Evaluating_Name": row.Student_Evaluating_Name, "Status": row.Status, "Due_Date": row.Due_Date, "Scheduled_Eval_Name": row.Scheduled_Eval_Name}
            for row in evaluations
        ]
        print("i reach here")
        return jsonify(evaluations)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# # @app.route('/evaluation_form', methods = ['GET'])
# # def evaluation_form():
# #     firstName = request.args.get("firstName")
# #     lastName = request.args.get("lastName")
# #     print(firstName)
# #     print(lastName)
# #     return render_template('test2.html')

# @app.route('/test_input_content', methods=('POST', 'GET'))
# def test_input_content():
#     inputContent = request.form.get("sampleInput")
#     inputContentTwo = request.form.get("sampleInputTwo")
#     print(inputContent)
#     print(inputContentTwo)
#     sql = """
# CREATE TABLE LaasiIsGonnaSlayTechTut (
#     ID INT,
#     FName VARCHAR(100),
#     LName VARCHAR(100)
# );
# """
#     cursor.execute(sql)
#     # sql = "INSERT INTO test_table (inputContent1, inputContent2) VALUES (%s, %s)"
#     # cursor.execute(sql, [inputContent, inputContentTwo])
#     conn.commit()
#     # print(sql)
#     # print(inputContent)

#     return "test completed!"

# app.secret_key = 'your_secret_key'

 

# # @app.route('/studentLogin', methods=['GET', 'POST'])

# # def studentLogin():

# #     if request.method == 'POST':
# #         print("reached 1")
# #         email = request.form['email']

# #         password = request.form['password']
# #         print("reached 2")
# #         print(email)

       

# #         try:

# #             # Query the database for the user with the provided email and password

# #             sql = "SELECT * FROM Student WHERE Email = %s AND Password = %s"

# #             cursor.execute(sql, (email, password))

# #             user = cursor.fetchone()
# #             print("look here")
# #             print(user['Student_Name'])

           

# #             if user:

# #                 # Store user information in session

# #                 session['user'] = user

# #                 print("User session set:", session['user'])

# #                 flash('Login successful!', 'success')

# #                 return redirect(url_for('test'))

# #             else:

# #                 flash('Incorrect email or password. Please try again.', 'error')

# #                 return redirect(url_for('studentLogin'))

# #         except Exception as e:

# #             flash('An error occurred: {}'.format(str(e)), 'error')

# #             return redirect(url_for('studentLogin'))

 

# #     return render_template('studentLogin.html')
# #     # return render_template('test.html', )

 

# if __name__ == '__main__':

#     app.run(debug=True)





@app.route('/form/<string:beingEval>/<string:evaluatorName>/<string:evaluationName>')
def form(beingEval, evaluatorName, evaluationName):
    try:
        # student_being_evaluated = request.args.get('beingEval')
        return render_template('form.html', student_name=beingEval, evaluator_name=evaluatorName, evaluationName=evaluationName)

    except Exception as e:

        print(f"Error: {e}")

        return "An error occurred", 500




@app.route('/submit_evaluation/<evaluator_name>', methods=['POST'])

def submit_evaluation(evaluator_name):

    if request.method == 'POST':

        try:

            # Fetch data from the form

            Team_Member_Name = request.form['Team_Member_Name']
            Evaluation_Name = request.form['evaluationName']

            Group_Effort_Peer = int(request.form['topic1'])

            Completes_Tasks_On_Time_Peer = int(request.form['topic2'])

            Provides_Useful_Feedback_Peer = int(request.form['topic3'])

            Communicates_Effectively_Peer = int(request.form['topic4'])

            Accepts_Contribution_Peer = int(request.form['topic5'])

            Builds_Contributions_Peer = int(request.form['topic6'])

            Group_Role_Peer = int(request.form['topic7'])

            Clarifies_Goals_Peer = int(request.form['topic8'])

            Reports_To_Team_Peer = int(request.form['topic9'])

            Ensures_Consistency_Peer = int(request.form['topic10'])

            Positivity_Peer = int(request.form['topic11'])

            Appropriate_Assertiveness_Peer = int(request.form['topic12'])

            Appropriate_Contibution_Peer = int(request.form['topic13'])

            Manages_Conflict_Peer = int(request.form['topic14'])

            Overall_Score_Peer = int(request.form['topic15'])

 

            # cursor.execute('SELECT MAX(Eval_ID) FROM Evaluation')

            # max_eval_id = cursor.fetchone()[0]

            # if max_eval_id is None:

            #     max_eval_id = 0

            # new_eval_id = max_eval_id + 1

 

            # Print form data for debugging

            # print(f"Form Data: {new_eval_id}, {Team_Member_Name}, {Group_Effort_Peer}, {Completes_Tasks_On_Time_Peer}, {Provides_Useful_Feedback_Peer}, {Communicates_Effectively_Peer}, {Accepts_Contribution_Peer}, {Builds_Contributions_Peer}, {Group_Role_Peer}, {Clarifies_Goals_Peer}, {Reports_To_Team_Peer}, {Ensures_Consistency_Peer}, {Positivity_Peer}, {Appropriate_Assertiveness_Peer}, {Appropriate_Contibution_Peer}, {Manages_Conflict_Peer}, {Overall_Score_Peer}")
            print(f"Form Data: {Team_Member_Name}, {Group_Effort_Peer}, {Completes_Tasks_On_Time_Peer}, {Provides_Useful_Feedback_Peer}, {Communicates_Effectively_Peer}, {Accepts_Contribution_Peer}, {Builds_Contributions_Peer}, {Group_Role_Peer}, {Clarifies_Goals_Peer}, {Reports_To_Team_Peer}, {Ensures_Consistency_Peer}, {Positivity_Peer}, {Appropriate_Assertiveness_Peer}, {Appropriate_Contibution_Peer}, {Manages_Conflict_Peer}, {Overall_Score_Peer}")

 

            # Insert data into the Evaluation table

            sql = '''

                INSERT INTO Evaluation (Evaluator_Name, Team_Member_Name, Group_Effort_Peer, Completes_Tasks_On_Time_Peer, Provides_Useful_Feedback_Peer, Communicates_Effectively_Peer, Accepts_Contribution_Peer, Builds_Contributions_Peer, Group_Role_Peer, Clarifies_Goals_Peer, Reports_To_Team_Peer, Ensures_Consistency_Peer, Positivity_Peer, Appropriate_Assertiveness_Peer, Appropriate_Contibution_Peer, Manages_Conflict_Peer, Overall_Score_Peer)

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            '''
            # sql = '''

            #     INSERT INTO Evaluation (Eval_ID, Team_Member_Name, Group_Effort_Peer, Completes_Tasks_On_Time_Peer, Provides_Useful_Feedback_Peer, Communicates_Effectively_Peer, Accepts_Contribution_Peer, Builds_Contributions_Peer, Group_Role_Peer, Clarifies_Goals_Peer, Reports_To_Team_Peer, Ensures_Consistency_Peer, Positivity_Peer, Appropriate_Assertiveness_Peer, Appropriate_Contibution_Peer, Manages_Conflict_Peer, Overall_Score_Peer)

            #     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            # '''

            queryForID = """
            SELECT Student_ID
            FROM [peer-eval-db].dbo.Student
            WHERE Student_Name = ?
            """
            cursor.execute(queryForID, (Team_Member_Name,))
            being_evaluated_id = cursor.fetchone()[0]

            cursor.execute(queryForID, (evaluator_name,))
            evaluating_id = cursor.fetchone()[0]



            sql1 = '''
                UPDATE Scheduled_Eval
                SET Status = 'Complete'
                WHERE Student_Being_Evaluated_ID = ?
                AND Student_Evaluating_ID = ?
                AND Scheduled_Eval_Name = ?;      
                '''
            cursor.execute(sql1, (being_evaluated_id, evaluating_id, Evaluation_Name))

            # cursor.execute(sql, (new_eval_id, Team_Member_Name, Group_Effort_Peer, Completes_Tasks_On_Time_Peer, Provides_Useful_Feedback_Peer, Communicates_Effectively_Peer, Accepts_Contribution_Peer, Builds_Contributions_Peer, Group_Role_Peer, Clarifies_Goals_Peer, Reports_To_Team_Peer, Ensures_Consistency_Peer, Positivity_Peer, Appropriate_Assertiveness_Peer, Appropriate_Contibution_Peer, Manages_Conflict_Peer, Overall_Score_Peer))
            cursor.execute(sql, (evaluator_name, Team_Member_Name, Group_Effort_Peer, Completes_Tasks_On_Time_Peer, Provides_Useful_Feedback_Peer, Communicates_Effectively_Peer, Accepts_Contribution_Peer, Builds_Contributions_Peer, Group_Role_Peer, Clarifies_Goals_Peer, Reports_To_Team_Peer, Ensures_Consistency_Peer, Positivity_Peer, Appropriate_Assertiveness_Peer, Appropriate_Contibution_Peer, Manages_Conflict_Peer, Overall_Score_Peer))

            conn.commit()

 

            flash('Evaluation submitted successfully!', 'success')
            # return render_template('index.html')

            return redirect(url_for('student_home'))

        except Exception as e:

            conn.rollback()

            print(f"Error: {e}")

            flash(f"An error occurred: {e}", 'error')

            return f"An error occurred: {e}", 500

 

    # return render_template('success.html')

@app.route('/forgot_password_email', methods=['GET', 'POST'])
def forgot_password_email():
    return render_template('forget_password_email.html')

@app.route('/forgot_password_reset', methods=['GET', 'POST'])
def forgot_password_reset():
    return render_template('forget_password_reset.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        # Check if the email exists in either Student or Professor table
        cursor.execute('SELECT COUNT(*) FROM Student WHERE Email = ?', (email,))
        student_exists = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM Professor WHERE Professor_Email = ?', (email,))
        professor_exists = cursor.fetchone()[0]

        if not student_exists and not professor_exists:
            flash('This email does not exist. Try signing up.', 'error')
            return redirect(url_for('sign_up'))
        else:
            # Save the email in the session for the next page
            session['email'] = email
            return redirect(url_for('reset_password'))

    return redirect(url_for('forgot_password_email'))


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        email = session.get('email')

        if not email:
            flash('Session expired. Please try again.', 'error')
            return redirect(url_for('forgot_password'))

        # Update the password in the correct table
        cursor.execute('UPDATE Student SET Password = ? WHERE Email = ?', (new_password, email))
        student_updated = cursor.rowcount > 0  # Check if any row was updated

        if not student_updated:
            cursor.execute('UPDATE Professor SET Password = ? WHERE Professor_Email = ?', (new_password, email))
            professor_updated = cursor.rowcount > 0

        conn.commit()

        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('sign_in'))

    return redirect(url_for('forgot_password_reset'))
