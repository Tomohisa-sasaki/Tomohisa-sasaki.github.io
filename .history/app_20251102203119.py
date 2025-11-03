<file name=templates/base.html path=/Users/tomohisa/flask_muscle_app/templates><!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Muscle App</title>
</head>
<body>
    <nav>
        <a href="{{ url_for('index') }}">Home</a> |
        <a href="{{ url_for('new_workout') }}">New workout</a>
    </nav>
    {% block content %}{% endblock %}
</body>
</html>
</file>