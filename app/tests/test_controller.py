import unittest
from app import app, db
from app.models.project import Project
from app.models.tag import Tag
from app.models.description import Description
from requests import Response
from unittest.mock import patch, MagicMock
import requests
from os import environ
from sqlalchemy import select
from datetime import date
import json
# Define the JWT token as a constant outside the test class
JWT_TOKEN_GOOD = 'your_test_token'
JWT_TOKEN_BAD = 'your_bad_token'
environment = environ
VERIFY_URL = environment["VERIFY_URL"]
class AuthTestCase(unittest.TestCase):
    def setUp(self):
        # Set up the Flask app for testing
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'sekrit!'
        
        # Create a mock function for requests.get
        self.mock_get = patch.object(requests, 'get', side_effect=self._mocked_get).start()

        with app.app_context():
            # Create the database tables
            db.create_all()
        self.app = app.test_client()

    def tearDown(self):
        with app.app_context():
            # Clean up the database tables
            db.session.remove()
            db.drop_all()
        # Stop the mock for requests.get
        self.mock_get.stop()

    def _mocked_get(self, url, headers, **kwargs):
        # Check if the URL and headers are correct
        if url == VERIFY_URL and headers.get('Authorization') == f'Bearer {JWT_TOKEN_GOOD}':
            # Create a mock response
            expected_response = Response()
            expected_response.status_code = 200
            data = {"username": environment["ADMIN_LIST"].split(",")[0]}
            data_json_string = json.dumps(data)
            data_bytes = data_json_string.encode('utf-8')
            expected_response._content = data_bytes
            return expected_response
        elif url == VERIFY_URL and headers.get('Authorization') == f'Bearer {JWT_TOKEN_BAD}':
            # Create a mock response for bad permissions (Unauthorized)
            expected_response = Response()
            expected_response.status_code = 401
            expected_response._content = b'{"username": "test2"}'
            return expected_response
        else:
            # Unexpected URL or headers, return a mock response with 404 status code
            expected_response = Response()
            expected_response.status_code = 401
            expected_response._content = b'{"msg": "Missing JWT in headers or cookies (Missing Authorization Header; Missing cookie \"access_token_cookie\")"}'
            return expected_response

    def test_create_project_endpoint(self):
        with app.app_context():
            http_method = self.app.post
            endpoint = "projects/"
            # Test with bad permissions (Unauthorized)
            response = http_method(endpoint, json={}, headers={'Authorization': f'Bearer {JWT_TOKEN_BAD}'})
            self.assertEqual(response.status_code, 401)

            # Test without title (Bad Request)
            response = http_method(endpoint, json={'overview': 'Test overview'}, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 400)

            # Test without overview (Bad Request)
            response = http_method(endpoint, json={'title': 'Test title'}, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 400)

            # Test without title and overview (Bad Request)
            response = http_method(endpoint, json={}, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 400)

            # Test with title and overview (Created)
            last_count_p = Project.query.count()
            response = http_method(endpoint, json={'title': 'Test title', 'overview': 'Test overview'}, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Project.query.count(), last_count_p + 1)

            # Test with tags and descriptions (Created)
            last_count_p = Project.query.count()
            last_count_t = Tag.query.count()
            last_count_d = Description.query.count()
            response = http_method(endpoint, json={
                'title': 'Test title1',
                'overview': 'Test overview',
                'tags': ['tag1', 'tag2'],
                'description': ['description1', 'description2']
            }, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(Project.query.count(), last_count_p + 1)
            self.assertEqual(Tag.query.count(), last_count_t + 2)
            self.assertEqual(Description.query.count(), last_count_d + 2)
            # Test if tags are created and associated with the project
            project = db.session.query(Project).where(Project.title==response.json["title"]).first()
            tags = project.tags
            self.assertEqual(len(tags), 2)
            self.assertIn('tag1', [tag.name for tag in tags])
            self.assertIn('tag2', [tag.name for tag in tags])

    def test_get_projects(self):
        with app.app_context():
            http_method = self.app.get
            endpoint = "projects/"
            # Ensure the database is empty
            self.assertEqual(Project.query.count(), 0)

            # Test when the database is empty
            response = http_method(endpoint)
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 0)

            # Test when there are two projects
            project1 = Project(title='Project 1', overview='Overview 1')
            project2 = Project(title='Project 2', overview='Overview 2')
            db.session.add(project1)
            db.session.add(project2)
            db.session.commit()

            response = http_method(endpoint)
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 2)
            # You can also check the details of the projects if needed

            # Test when there are multiple projects
            # Add more projects to the database
            project3 = Project(title='Project 3', overview='Overview 3')
            project4 = Project(title='Project 4', overview='Overview 4')
            db.session.add(project3)
            db.session.add(project4)
            db.session.commit()

            response = http_method(endpoint)
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 4)
            # You can also check the details of the projects if needed

    def test_get_project_by_title(self):
        with app.app_context():
            http_method = self.app.get
            endpoint = "projects/find/"

            # Ensure the database is empty
            self.assertEqual(Project.query.count(), 0)
            basic_title = "Test_Project"
            space_title = "Test pro"
            basic_overview = "Test overview"
            # Add a project to the database
            project = Project(title=basic_title, overview=basic_overview)
            db.session.add(project)
            db.session.commit()
            project = Project(title=space_title, overview=basic_overview)
            db.session.add(project)
            db.session.commit()

            # Test when the project is found by exact title
            response = http_method(endpoint + basic_title)
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data["title"], basic_title)
            self.assertEqual(data["description"], basic_overview)

            # Test when the project is not found by non-existing title
            response = http_method(endpoint + 'Non_Existing_Project')
            data = response.get_json()
            self.assertEqual(response.status_code, 404)
            self.assertEqual(data["message"], "Project not found")

            # Test when all characters are replaced with wildcards, should not return any results
            response = http_method(endpoint + '_'*len(basic_title) )
            data = response.get_json()
            self.assertEqual(response.status_code, 404)
            self.assertEqual(data["message"], "Project not found")

            # Add a project with title containing underscores

            # Test when the project is found by title with underscores
            response = http_method(endpoint + space_title.replace(" ", "_"))
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data["title"], space_title)
            self.assertEqual(data["description"], basic_overview)


    def test_tag_endpoints(self):
        with app.app_context():
            http_method = self.app.get
            endpoint1 = "projects/tag/"
            endpoint2 = "projects/tags"
            response = http_method("projects/")
            self.assertEqual(response.status_code, 200)

            # Ensure the database is empty
            self.assertEqual(Project.query.count(), 0)
            self.assertEqual(Tag.query.count(), 0)
            p1t, p2t, p3t, p4t = (f"Test Project {x}" for x in range(1,5))
            t1n, t2n, t3n, t4n, t5n = (f"Tag {x}" for x in range(1,6))
            overview = "Test overview"

            # Test get_tags_with_projects no tags exist
            response = http_method(endpoint2)
            data = response.get_json()
            self.assertEqual(response.status_code, 404)
            self.assertEqual(data["message"], "No tags with projects found")

            tag1 = Tag(name=t1n)
            db.session.add(tag1)
            db.session.commit()

            tag2 = Tag(name=t2n)
            db.session.add(tag2)
            db.session.commit()
            
            tag3 = Tag(name=t3n)
            db.session.add(tag3)
            db.session.commit()
            
            tag4 = Tag(name=t4n)
            db.session.add(tag4)
            db.session.commit()

            tag5 = Tag(name=t5n)
            db.session.add(tag5)
            db.session.commit()
            # Add a project and tag to the database
            
            # Test get_tags_with_projects no tags have projects
            response = http_method(endpoint2)
            data = response.get_json()
            self.assertEqual(response.status_code, 404)
            self.assertEqual(data["message"], "No tags with projects found")
            
            project1 = Project(title=p1t, overview=overview)
            project1.tags = [tag1, tag2]
            db.session.add(project1)
            db.session.commit()

            project2 = Project(title=p2t, overview=overview)
            project2.tags = [tag2]
            db.session.add(project2)
            db.session.commit()

            project3 = Project(title=p3t, overview=overview)
            project3.tags = [tag3]
            db.session.add(project3)
            db.session.commit()

            project4 = Project(title=p4t, overview=overview)
            project4.tags = [tag1, tag2, tag3, tag4]
            db.session.add(project4)
            db.session.commit()


            # Test get_projects_by_tag when the project is found by tag
            response = http_method(endpoint1 + t4n)
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["title"], p4t)

            response = http_method(endpoint1 + t2n)
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 3)

            # Test get_projects_by_tag when no projects are found with the specified tag
            response = http_method(endpoint1 + t5n)
            data = response.get_json()
            self.assertEqual(response.status_code, 404)
            self.assertEqual(data["message"], "No projects found with the specified tag")

            # Test get_projects_by_tag when no tag exists
            response = http_method(endpoint1 + "not_a_tag")
            data = response.get_json()
            self.assertEqual(response.status_code, 404)
            self.assertEqual(data["message"], "No tags found with the specified name")

            # Test get_tags_with_projects when a tag with associated projects is found
            response = http_method(endpoint2)
            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(data), 4)


    def test_update_project_endpoint(self):
        with app.app_context():
            http_method = self.app.put
            endpoint = "projects/"

            # Ensure the database is empty
            self.assertEqual(Project.query.count(), 0)
            init_t = "first title"
            upda_t = "second title"
            init_o = "first overview"
            upda_o = "second overview"
            init_gh = "github.com/first"
            upda_gh = "github.com/second"
            init_sd = "1970-01"
            init_sd_db = date(year=1970, month=1, day=1)
            upda_sd = "2023-04"
            upda_sd_db = date(year=2023, month=4, day=1)
            init_ed = "1970-01"
            init_ed_db = date(year=1970, month=1, day=1)
            upda_ed = "2023-07"
            upda_ed_db = date(year=2023, month=7, day=1)
            #tags
            t1n, t2n, t3n, t4n, t5n = (f"Tag {x}" for x in range(1,6))
            tag1 = Tag(name=t1n)
            tag1.save()
            tag2 = Tag(name=t2n)
            tag2.save()
            tag3 = Tag(name=t3n)
            tag3.save()

            init_tags = [tag1.name, tag2.name]
            upda_tags = [tag2.name, tag3.name]      
            init_f = ["description1", "description2"]
            upda_f = ["description3", "description4"]  
            init_data = {
                'title': init_t,
                'overview': init_o,
                'github_link': init_gh,
                'start_date': init_sd,
                'end_date': init_ed,
                'tags': init_tags,  # Updating tags by name
                'descriptions': init_f,          # Updating descriptions
            }
            # Test updating a non-existent project
            response = http_method(endpoint + "12345", json={'title': upda_t}, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 404)
            data = response.get_json()

            # Add a project to the database
            project = Project(title=init_t, overview=init_o,github_link=init_gh, start_date=init_sd, end_date=init_ed, tags=init_tags, descriptions=init_f)
            project.save()
            id = project.id

            # Test updating a project with invalid data
            response = http_method(endpoint + str(id), json={}, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 400)
            data = response.get_json()

            # Test updating a project with valid data
            updated_data = {
                'title': 'Updated title',
                'overview': 'Updated overview',
            }
            response = http_method(endpoint + str(project.id), json=updated_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = Project.query.filter(Project.id==project.id).first()
            self.assertEqual(updated_project.title, updated_data['title'])
            self.assertEqual(updated_project.overview, updated_data['overview'])

            # Test updating a project with invalid permissions (Unauthorized)
            response = http_method(endpoint + str(project.id), json=updated_data, headers={'Authorization': f'Bearer {JWT_TOKEN_BAD}'})
            self.assertEqual(response.status_code, 401)
            

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})

            updated_data = {
                'title': upda_t,
                'overview': upda_o,
                'github_link': upda_gh,
                'start_date': upda_sd,
                'end_date': upda_ed,
                'tags': [tag2.name, tag3.name],  # Updating tags by name
                'descriptions': upda_f,          # Updating descriptions
            }
            response = http_method(endpoint + str(project.id), json=updated_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, updated_data['title'])
            self.assertEqual(updated_project.overview, updated_data['overview'])
            self.assertEqual(updated_project.github_link, updated_data['github_link'])
            self.assertEqual(updated_project.start_date, upda_sd_db)
            self.assertEqual(updated_project.end_date, upda_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(updated_data['tags']))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(updated_data['descriptions']))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
                        # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})

            #UPDATE ONLY TITLE
            updated_data_2 = {
                'title': upda_t,
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, upda_t)
            self.assertEqual(updated_project.overview, init_o)
            self.assertEqual(updated_project.github_link, init_gh)
            self.assertEqual(updated_project.start_date, init_sd_db)
            self.assertEqual(updated_project.end_date, init_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(init_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(init_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})


            #UPDATE ONLY OVEWVIEW
            updated_data_2 = {
                'overview': upda_o,
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, init_t)
            self.assertEqual(updated_project.overview, upda_o)
            self.assertEqual(updated_project.github_link, init_gh)
            self.assertEqual(updated_project.start_date, init_sd_db)
            self.assertEqual(updated_project.end_date, init_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(init_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(init_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})

            
            #UPDATE ONLY GITHUB
            updated_data_2 = {
                'github_link': upda_gh,
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, init_t)
            self.assertEqual(updated_project.overview, init_o)
            self.assertEqual(updated_project.github_link, upda_gh)
            self.assertEqual(updated_project.start_date, init_sd_db)
            self.assertEqual(updated_project.end_date, init_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(init_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(init_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})

            
            #UPDATE ONLY START DATE
            updated_data_2 = {
                'start_date': upda_sd,
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, init_t)
            self.assertEqual(updated_project.overview, init_o)
            self.assertEqual(updated_project.github_link, init_gh)
            self.assertEqual(updated_project.start_date, upda_sd_db)
            self.assertEqual(updated_project.end_date, init_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(init_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(init_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})

            
            #UPDATE ONLY END DATE
            updated_data_2 = {
                'end_date': upda_ed,
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, init_t)
            self.assertEqual(updated_project.overview, init_o)
            self.assertEqual(updated_project.github_link, init_gh)
            self.assertEqual(updated_project.start_date, init_sd_db)
            self.assertEqual(updated_project.end_date, upda_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(init_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(init_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})

            
            #UPDATE ONLY TAGS
            updated_data_2 = {
                'tags': upda_tags,
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, init_t)
            self.assertEqual(updated_project.overview, init_o)
            self.assertEqual(updated_project.github_link, init_gh)
            self.assertEqual(updated_project.start_date, init_sd_db)
            self.assertEqual(updated_project.end_date, init_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(upda_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(init_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})



            #UPDATE ONLY features
            updated_data_2 = {
                'descriptions': upda_f, 
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, init_t)
            self.assertEqual(updated_project.overview, init_o)
            self.assertEqual(updated_project.github_link, init_gh)
            self.assertEqual(updated_project.start_date, init_sd_db)
            self.assertEqual(updated_project.end_date, init_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(init_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(upda_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})

            #UPDATE TO THE SAME
            updated_data_2 = {
                'descriptions': init_f,
                'tags': init_tags,
                'start_date':init_sd, 
            }
            response = http_method(endpoint + str(project.id), json=updated_data_2, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)
            updated_project = db.session.get(Project, project.id)
            self.assertEqual(updated_project.title, init_t)
            self.assertEqual(updated_project.overview, init_o)
            self.assertEqual(updated_project.github_link, init_gh)
            self.assertEqual(updated_project.start_date, init_sd_db)
            self.assertEqual(updated_project.end_date, init_ed_db)

            # Assert tags are updated
            updated_tags = [tag.name for tag in updated_project.tags]
            self.assertEqual(set(updated_tags), set(init_tags))

            # Assert descriptions are updated
            updated_descriptions = [desc.description for desc in updated_project.descriptions]
            self.assertEqual(set(updated_descriptions), set(init_f))

            # reset object
            response = http_method(endpoint + str(project.id), json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
    
    
    def test_update_tag_endpoint(self):
        with app.app_context():

            # Ensure the database is empty
            self.assertEqual(Project.query.count(), 0)
            init_t = "first title"
            init_o = "first overview"
            #tags
            t1n, t2n, t3n, t4n, t5n = (f"Tag {x}" for x in range(1,6))
            tag1 = Tag(name=t1n)
            tag1.save()

            init_tags = [tag1.name]
            init_data = {
                'title': init_t,
                'overview': init_o,
                'tags': init_tags,
            }
            # Test updating a non-existent project
            response = self.app.post("/projects/", json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
        
            http_method = self.app.put
            endpoint = "projects/tag/"
            # Ensure the database is empty (if required for your test)
            self.assertEqual(Tag.query.count(), 1)

            # Prepare the updated data
            updated_tag_name = "Updated Tag"
            updated_data = {
                'name': updated_tag_name,
            }

            #Test updating a tag that doesn't exist
            response = http_method(endpoint + "1234412", json={"name": "bad tag"}, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 404)
            self.assertEqual(Tag.query.count(), 1)
            # Test updating a tag with a valid JWT token
            response = http_method(endpoint + str(tag1.id), json=updated_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 200)

            # Verify the response and database changes
            updated_tag = db.session.get(Tag, tag1.id)
            self.assertEqual(Tag.query.count(), 1)
            self.assertEqual(updated_tag.name, updated_tag_name)

            # Test updating a tag with an invalid JWT token
            response = http_method(endpoint + str(tag1.id), json=updated_data, headers={'Authorization': f'Bearer {JWT_TOKEN_BAD}'})
            self.assertEqual(response.status_code, 401)

    def test_delete_project_endpoint(self):
        with app.app_context():
            http_method = self.app.delete
            endpoint = "/projects/"
            # Create a test project
            init_t = "Test Project"
            init_o = "Test Overview"
            init_tags = ["Tag 1"]
            init_data = {
                'title': init_t,
                'overview': init_o,
                'tags': init_tags,
            }
            response = self.app.post('/projects/', json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 201)
            test_project_id = response.get_json()['id']

            # Send a DELETE request to delete the test project
            response = http_method(endpoint + str(test_project_id), headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 204)

            # Attempt to delete the test project again (it should return 404 since it's already deleted)
            response = http_method(endpoint + str(test_project_id), headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 404)

            # Attempt to delete a non-existent project with ID 12345
            response = http_method(endpoint + "12345", headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 404)
    
    def test_delete_tag_endpoint(self):
        with app.app_context():
            http_method = self.app.delete
            endpoint = "/projects/tag/"
            # Create a test project
            init_t = "Test Project"
            init_o = "Test Overview"
            tag_name = "tag1"
            init_tags = [tag_name]
            init_data = {
                'title': init_t,
                'overview': init_o,
                'tags': init_tags,
            }
            response = self.app.post('/projects/', json=init_data, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 201)
            test_tag_id = response.get_json()['tags'][0]["name"]
            tag = Tag.query.filter(Tag.name.like(tag_name)).first()
            self.assertIsNotNone(tag)

            #normal delete
            self.assertEqual(tag_name,response.get_json()['tags'][0]["name"])
            response = http_method(endpoint + tag_name, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 204)
            db_tag = db.session.get(Tag, test_tag_id)
            self.assertIsNone(db_tag)
            # Attempt to delete the test project again (it should return 404 since it's already deleted)
            response = http_method(endpoint + tag_name, headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 404)

            # Attempt to delete a non-existent project with ID 12345
            response = http_method(endpoint +  "not_real_tag", headers={'Authorization': f'Bearer {JWT_TOKEN_GOOD}'})
            self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
