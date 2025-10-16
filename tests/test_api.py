"""
Tests for the FastAPI Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Test the main API endpoints"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to static page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
    
    def test_get_activities(self, client, reset_activities):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0
        
        # Check that Chess Club exists with expected structure
        assert "Chess Club" in activities
        chess_club = activities["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupEndpoint:
    """Test the signup functionality"""
    
    def test_successful_signup(self, client, reset_activities):
        """Test successful student signup"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "message" in result
        assert "newstudent@mergington.edu" in result["message"]
        assert "Chess Club" in result["message"]
        
        # Verify the student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that duplicate signup is prevented"""
        # First signup should succeed
        response1 = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response1.status_code == 400
        
        result = response1.json()
        assert "already signed up" in result["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        result = response.json()
        assert "Activity not found" in result["detail"]
    
    def test_signup_missing_email(self, client, reset_activities):
        """Test signup without email parameter"""
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422  # Validation error


class TestUnregisterEndpoint:
    """Test the unregister functionality"""
    
    def test_successful_unregister(self, client, reset_activities):
        """Test successful student unregistration"""
        # First verify the student is registered
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        
        # Unregister the student
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "Unregistered" in result["message"]
        assert "michael@mergington.edu" in result["message"]
        
        # Verify the student was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_not_registered_student(self, client, reset_activities):
        """Test unregistering a student who is not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        result = response.json()
        assert "not signed up" in result["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregistering from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        result = response.json()
        assert "Activity not found" in result["detail"]
    
    def test_unregister_missing_email(self, client, reset_activities):
        """Test unregister without email parameter"""
        response = client.delete("/activities/Chess Club/unregister")
        assert response.status_code == 422  # Validation error


class TestDataIntegrity:
    """Test data integrity and business logic"""
    
    def test_participant_count_accuracy(self, client, reset_activities):
        """Test that participant counts are accurate"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity in activities.items():
            participant_count = len(activity["participants"])
            max_participants = activity["max_participants"]
            
            # Check that current participants don't exceed maximum
            assert participant_count <= max_participants
            
            # Check that all participants have valid email format
            for participant in activity["participants"]:
                assert "@" in participant
                assert "." in participant
    
    def test_activity_structure_consistency(self, client, reset_activities):
        """Test that all activities have consistent structure"""
        response = client.get("/activities")
        activities = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity in activities.items():
            for field in required_fields:
                assert field in activity, f"Activity '{activity_name}' missing field '{field}'"
            
            # Check data types
            assert isinstance(activity["description"], str)
            assert isinstance(activity["schedule"], str)
            assert isinstance(activity["max_participants"], int)
            assert isinstance(activity["participants"], list)
            assert activity["max_participants"] > 0
    
    def test_activity_signup_flow(self, client, reset_activities):
        """Test complete signup and unregister flow"""
        test_email = "testflow@mergington.edu"
        activity_name = "Programming Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity_name]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup_response = client.get("/activities")
        after_signup_count = len(after_signup_response.json()[activity_name]["participants"])
        assert after_signup_count == initial_count + 1
        assert test_email in after_signup_response.json()[activity_name]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister?email={test_email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity_name]["participants"])
        assert final_count == initial_count
        assert test_email not in final_response.json()[activity_name]["participants"]


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_special_characters_in_email(self, client, reset_activities):
        """Test signup with special characters in email"""
        import urllib.parse
        
        special_email = "test+special.email@mergington.edu"
        encoded_email = urllib.parse.quote(special_email)
        
        response = client.post(
            f"/activities/Art Club/signup?email={encoded_email}"
        )
        assert response.status_code == 200
        
        # Verify the email was properly stored
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert special_email in activities["Art Club"]["participants"]
    
    def test_activity_name_with_spaces(self, client, reset_activities):
        """Test that activity names with spaces work correctly"""
        response = client.post(
            "/activities/Drama Society/signup?email=drama@mergington.edu"
        )
        assert response.status_code == 200
    
    def test_case_sensitive_activity_names(self, client, reset_activities):
        """Test that activity names are case sensitive"""
        response = client.post(
            "/activities/chess club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404  # Should not find "chess club" (lowercase)
    
    def test_url_encoded_activity_names(self, client, reset_activities):
        """Test URL encoding in activity names"""
        import urllib.parse
        
        activity_name = "Drama Society"
        encoded_name = urllib.parse.quote(activity_name)
        
        response = client.post(
            f"/activities/{encoded_name}/signup?email=encoded@mergington.edu"
        )
        assert response.status_code == 200