from app import db
import app.models.tag as tag_ns
from app.models.description import Description
from sqlalchemy.orm import relationship
import re
from logging import warning
import logging
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    github_link = db.Column(db.String(255))
    overview = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # Define the many-to-many relationship with tags
    tags = db.relationship(tag_ns.Tag, secondary=tag_ns.project_tags, overlaps="projects")

    # Define the one-to-many relationship with descriptions
    descriptions = db.relationship('Description', backref='project', lazy=True, cascade='all, delete-orphan')

    def __init__(self, title, overview, github_link=None, start_date=None, end_date=None, descriptions=None, tags=None):
        self.title = title
        self.github_link = github_link
        self.overview = overview
        if start_date:
            self.start_date = self._complete_date(start_date)
        else:
            self.start_date = None
        if end_date:
            self.end_date = self._complete_date(end_date)
        else:
            self.end_date = None
        self.descriptions = []
        if descriptions:
            for item in descriptions:
                if not isinstance(item, Description):
                    item = Description(item, self)
                self.descriptions.append(item)
        self.tags = []
        if tags:
            for item in tags:
                if not isinstance(item, tag_ns.Tag):           
                    in_db = tag_ns.Tag.query.filter_by(name=item).first()
                    if in_db:
                        item = in_db
                    else:
                        item =tag_ns.Tag(name=item)
                self.tags.append(item)
    
    @staticmethod
    def _complete_date(date_str):
        if date_str is None:
            return None
        # Check if the date string is in the format "yyyy-mm"
        if re.match(r'^\d{4}-\d{2}$', date_str):
            # Complete the date to the first day of the month
            return f"{date_str}-01"
        return date_str


    def save(self):
        db.session.add(self)
        db.session.commit()     ###this is the line with the error

        for tag in self.tags:
            #query the database for the tag
            in_db = tag_ns.Tag.query.filter_by(name=tag.name).first()
            if not in_db:  # Check if the tag is not already saved
                tag.save()
            else:
                tag = in_db
            # Create the relationship record in the project_tags table
            # if it doesn't exist
            if not db.session.query(tag_ns.project_tags).filter_by(tag_id=tag.id, project_id=self.id).first():
                db.session.execute(tag_ns.project_tags.insert().values(tag_id=tag.id, project_id=self.id))
                db.session.commit()


        # Save related descriptions
        for description in self.descriptions:
            description.project_id = self.id
            description.save()

    def __repr__(self):
        return f'<Project {self.title}>'

    def serialize(self):
        # Create a dictionary representation of the Project object
        return {
            'id': self.id,
            'title': self.title,
            'overview': self.overview,
            'description': [description.description for description in self.descriptions],
            'githubLink': self.github_link,
            'tags': [tag.serialize() for tag in self.tags],
            'dates': [
                        self.start_date.strftime('%Y-%m') if self.start_date else None,
                        self.end_date.strftime('%Y-%m') if self.end_date else None
                    ],
        }
    
    def delete(self):
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
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        if start_date:
            self.start_date = self._complete_date(start_date)
        if end_date:
            self.end_date = self._complete_date(end_date)

        # Update tags if provided
        tags = kwargs.get('tags')
        if tags:
            # Clear the existing tags
            self.tags.clear()

            # Add the new tags
            for tag_name in tags:
                tag = tag_ns.Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    # If the tag doesn't exist, create a new one
                    tag = tag_ns.Tag(name=tag_name)
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
                description = Description(description=description_text, project=self)
                description.save()
        # Save the changes to the database
        db.session.commit()
        
    def get_tags(self):
        # Use joinedload to include the tags in the query result
        return db.session.query(tag_ns.project_tags).filter_by(project_id=self.id).all()