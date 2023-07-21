from app import db
from app.models.tag import project_tags
from app.models.description import Description

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    github_link = db.Column(db.String(255), nullable=False)
    overview = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # Define the many-to-many relationship with tags
    tags = db.relationship('Tag', secondary=project_tags, backref='project')

    # Define the one-to-many relationship with descriptions
    descriptions = db.relationship('Description', backref='project', lazy=True)
    
    def __init__(self, title, github_link, overview, start_date=None, end_date=None):
        self.title = title
        self.github_link = github_link
        self.overview = overview
        self.start_date = start_date
        self.end_date = end_date

    def save(self):
        db.session.add(self)
        db.session.commit()

        for tag in self.tags:
            if not tag.id:  # Check if the tag is not already saved
                db.session.add(tag)
                db.session.commit()  # Commit immediately to get the tag ID
            # Create the relationship record in the project_tags table
            # if it doesn't exist
            if not db.session.query(project_tags).filter_by(tag_id=tag.id, project_id=self.id).first():
                db.session.execute(project_tags.insert().values(tag_id=tag.id, project_id=self.id))
                db.session.commit()
            tag.save()


        # Save related descriptions
        for description in self.descriptions:
            description.save()

    def __repr__(self):
        return f'<Project {self.title}>'

    def serialize(self):
        # Create a dictionary representation of the Project object
        return {
            'id': self.id,
            'name': self.title,
            'description': self.overview,
            'features': [description.description for description in self.descriptions],
            'githubLink': self.github_link,
            'tags': [tag.name for tag in self.tags],
            'dates': [
                        self.start_date.strftime('%Y-%m') if self.start_date else None,
                        self.end_date.strftime('%Y-%m') if self.end_date else None
                    ],
        }
    
    def delete(self):
    # Delete related descriptions
        for description in self.descriptions:
            description.delete()

        # Remove the project from the tags association
        for tag in self.tags:
            self.tags.remove(tag)

        # Delete the project
        db.session.delete(self)
        db.session.commit()

    def update(self, **kwargs):
        if kwargs.get("args"):
            kwargs = kwargs.get("args")
        # Update the attributes with the new values if provided
        self.title = kwargs.get('title', self.title)
        self.github_link = kwargs.get('github_link', self.github_link)
        self.overview = kwargs.get('overview', self.overview)
        self.start_date = kwargs.get('start_date', self.start_date)
        self.end_date = kwargs.get('end_date', self.end_date)

        # Update tags if provided
        tags = kwargs.get('tags')
        if tags:
            # Clear the existing tags
            self.tags.clear()

            # Add the new tags
            for tag_name in tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    # If the tag doesn't exist, create a new one
                    tag = Tag(name=tag_name)
                    db.session.add(tag)

                self.tags.append(tag)

        # Update descriptions if provided
        descriptions = kwargs.get('descriptions')
        if descriptions:
            # Clear the existing descriptions
            for description in self.descriptions:
                db.session.delete(description)

            # Add the new descriptions
            for description_text in descriptions:
                description = Description(description=description_text, project_id=self.id)
                db.session.add(description)

        # Save the changes to the database
        db.session.commit()
