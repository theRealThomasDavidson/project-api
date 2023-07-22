from app import db
from app.models import project

class Description(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    # Define the many-to-one relationship with the Project model

    def __init__(self, description, project):
        self.description = description
        self.project_id = project.id

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def get_project(self):
        return project.Project.query.get(self.project_id).first()