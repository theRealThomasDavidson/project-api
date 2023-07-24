from flask import Blueprint, request, jsonify
from functools import wraps
import requests
from re import sub
from app import db
from os import environ

from app.models.project import Project
from app.models.tag import Tag
from app.models.description import Description
from logging import warning

# Create a Blueprint for the controller
controller_bp = Blueprint('controller', __name__)

environment = environ
VERIFY_URL = environment["VERIFY_URL"]
ADMIN_LIST = set(environment["ADMIN_LIST"].split(","))

def check_admin_permission(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the JWT token from the Authorization header
        jwt_token = request.headers.get('Authorization', '')

        # Verify the JWT token with the authentication service
        response = requests.get(VERIFY_URL, headers={'Authorization': f'{jwt_token}'})
        if response.status_code != 200:
            return jsonify({"error": "Unauthorized"}), 401
        data = response.json()
        username = data.get('username')

        # Check if the username exists in the admin list
        if username and username in ADMIN_LIST:
            return f(*args, **kwargs)

        # If the JWT is invalid or the user is not an admin, return an error response

    return decorated_function


@controller_bp.route('/admin', methods=['GET'])
@check_admin_permission
def check_admin():
    return jsonify({"message":"Approved"}), 204

#CREATE
@controller_bp.route('/', methods=['POST'])
@check_admin_permission
def create_project():
    data = request.get_json()
    title, overview = data.get('title'), data.get('overview')
    if not (title and overview):
        return jsonify({"message":"Project must include a title and overview"}), 400
    project = Project(
        title=title,
        github_link=data.get('github_link'),
        overview=overview,
        start_date=data.get('start_date'),
        end_date=data.get('end_date')
    )

    for tag_name in data.get("tags", []):
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            tag.save()
        project.tags.append(tag)

    # Add descriptions to the project if any are provided
    for description_text in data.get("description", []):
        description = Description(description=description_text, project=project)
        project.descriptions.append(description)
    # Save the project to the database
    project.save()

    return jsonify(project.serialize()), 201  # Return the created project with status code 201


#READ
# Define routes and their corresponding functions
@controller_bp.route('/', methods=['GET'])
def get_projects():
    # Retrieve all projects from the database
    projects = Project.query.all()
    # Serialize the projects to JSON and return the response
    return jsonify([project.serialize() for project in projects])

@controller_bp.route('find/<string:title>', methods=['GET'])
def get_project_by_title(title):
    title = sub(r'_+', '_', title)
    # Retrieve the project that matches the formatted title
    project = Project.query.filter(Project.title.like(title)).first()

    if project:
        # Serialize the project to JSON and return the response
        return jsonify(project.serialize())
    else:
        return jsonify({"message": "Project not found"}), 404


@controller_bp.route('/tag/<string:tag_name>', methods=['GET'])
def get_projects_by_tag(tag_name):
    tag_name = sub(r'_+', '_', tag_name)
    # Retrieve projects that have the specified tag
    tag = Tag.query.filter(Tag.name.like(tag_name)).first()
    if not tag:
        return jsonify({"message": "No tags found with the specified name"}), 404
    if not tag.projects:
        return jsonify({"message": "No projects found with the specified tag"}), 404
    return jsonify([project.serialize() for project in tag.projects])


@controller_bp.route('/tags', methods=['GET'])
def get_tags_with_projects():
    # Retrieve all tags that have at least one project associated with them
    tags_with_projects = Tag.query.filter(Tag.projects.any()).all()

    if tags_with_projects:
        # Serialize the tags to JSON and return the response
        return jsonify([tag.serialize() for tag in tags_with_projects])
    else:
        return jsonify({"message": "No tags with projects found"}), 404


#UPDATE
@controller_bp.route('/<int:project_id>', methods=['PUT'])
@check_admin_permission
def update_project(project_id):
    # Retrieve the project from the database by its ID
    project = Project.query.filter(Project.id==project_id).first()

    if not project:
        return jsonify({"message": "Project not found"}), 404
    data = request.json
    if not data:
        return jsonify({"message": "Body not readable"}), 400 
    project.update(args=data)
    return jsonify({"message": project.serialize()}), 200


@controller_bp.route('/tag/<int:tag_id>', methods=['PUT'])
@check_admin_permission
def update_tag(tag_id):
    # Retrieve the tag from the database by its ID
    tag = db.session.get(Tag, tag_id)

    if not tag:
        return jsonify({"message": "Tag not found"}), 404

    data = request.json
    if not data:
        return jsonify({"message": "Body not readable"}), 400

    # Update the tag attributes with the new values if provided
    tag.name = data.get('name', tag.name)

    tag.save()

    return jsonify({"message": tag.serialize()}), 200

#DELETE
@controller_bp.route('/<int:project_id>', methods=['DELETE'])
@check_admin_permission
def delete_project(project_id):
    # Retrieve the project by its ID
    project = db.session.get(Project, project_id)
    # project = Project.query.like(project_id)

    if project:
        # Delete the project from the database
        project.delete()
        return jsonify({"message": "Project deleted successfully"}), 204
    else:
        return jsonify({"message": "Project not found"}), 404


@controller_bp.route('/tag/<string:tag_name>', methods=['DELETE'])
@check_admin_permission
def delete_tag(tag_name):
    # Retrieve the tag by its ID
    tag = Tag.query.filter(Tag.name.like(tag_name)).first()

    if tag:
        # Delete the tag from the database
        tag.delete()
        return jsonify({"message": "Tag deleted successfully"}), 204
    else:
        return jsonify({"message": "Tag not found"}), 404
