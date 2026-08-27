"""
Feedback Manager - Handles user feedback, ratings, and suggestions.

This module provides:
- Feedback collection and storage
- User ratings for system performance
- Suggestion management
- Feedback analysis
"""

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback."""
    BUG = "bug"
    IMPROVEMENT = "improvement"
    QUESTION = "question"
    PRAISE = "praise"
    SUGGESTION = "suggestion"


class FeedbackStatus(Enum):
    """Status of feedback."""
    NEW = "new"
    REVIEWED = "reviewed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


@dataclass
class Feedback:
    """Represents user feedback."""
    feedback_id: str
    user: str = "anonymous"
    feedback_type: FeedbackType = FeedbackType.SUGGESTION
    subject: str = ""
    message: str = ""
    status: FeedbackStatus = FeedbackStatus.NEW
    priority: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None
    resolution: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "user": self.user,
            "feedback_type": self.feedback_type.value,
            "subject": self.subject,
            "message": self.message,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "resolution": self.resolution,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feedback":
        return cls(
            feedback_id=data.get("feedback_id", ""),
            user=data.get("user", "anonymous"),
            feedback_type=FeedbackType(data.get("feedback_type", "suggestion")),
            subject=data.get("subject", ""),
            message=data.get("message", ""),
            status=FeedbackStatus(data.get("status", "new")),
            priority=data.get("priority", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            resolved_at=data.get("resolved_at"),
            resolution=data.get("resolution", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class Rating:
    """Represents a user rating."""
    rating_id: str
    user: str = "anonymous"
    category: str = ""
    score: int = 3  # 1-5
    comments: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rating_id": self.rating_id,
            "user": self.user,
            "category": self.category,
            "score": self.score,
            "comments": self.comments,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rating":
        return cls(
            rating_id=data.get("rating_id", ""),
            user=data.get("user", "anonymous"),
            category=data.get("category", ""),
            score=data.get("score", 3),
            comments=data.get("comments", ""),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


class FeedbackManager:
    """
    Manages user feedback, ratings, and suggestions.
    
    This class:
    - Stores feedback in memory and optionally to disk
    - Provides methods for submitting and retrieving feedback
    - Analyzes feedback for trends
    - Manages feedback lifecycle
    """
    
    def __init__(self, storage_path: str = "feedback.json", user: str = "anonymous"):
        self.storage_path = Path(storage_path)
        self.user = user
        self._feedback: Dict[str, Feedback] = {}
        self._ratings: Dict[str, Rating] = {}
        self._lock = threading.RLock()
        self._next_id = 1
        
        # Load existing feedback
        self._load_feedback()
    
    def _load_feedback(self):
        """Load feedback from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for fb_data in data.get("feedback", []):
                        fb = Feedback.from_dict(fb_data)
                        self._feedback[fb.feedback_id] = fb
                        self._next_id = max(self._next_id, int(fb.feedback_id.replace("fb_", "")) + 1)
                    
                    for rt_data in data.get("ratings", []):
                        rt = Rating.from_dict(rt_data)
                        self._ratings[rt.rating_id] = rt
                
                logger.info(f"Loaded {len(self._feedback)} feedback items and {len(self._ratings)} ratings")
            except Exception as e:
                logger.warning(f"Failed to load feedback: {e}")
    
    def _save_feedback(self):
        """Save feedback to storage."""
        try:
            data = {
                "feedback": [fb.to_dict() for fb in self._feedback.values()],
                "ratings": [rt.to_dict() for rt in self._ratings.values()]
            }
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save feedback: {e}")
    
    def submit_feedback(self, feedback_type: FeedbackType, subject: str, 
                       message: str, priority: int = 0) -> str:
        """
        Submit new feedback.
        
        Args:
            feedback_type: Type of feedback (BUG, IMPROVEMENT, etc.)
            subject: Short subject/title
            message: Detailed message
            priority: Priority level (0-10)
        
        Returns:
            The feedback ID
        """
        with self._lock:
            feedback_id = f"fb_{self._next_id}"
            self._next_id += 1
            
            feedback = Feedback(
                feedback_id=feedback_id,
                user=self.user,
                feedback_type=feedback_type,
                subject=subject,
                message=message,
                priority=priority
            )
            
            self._feedback[feedback_id] = feedback
            self._save_feedback()
            
            logger.info(f"Feedback submitted: {feedback_id} - {subject}")
            return feedback_id
    
    def submit_rating(self, category: str, score: int, comments: str = "") -> str:
        """
        Submit a rating.
        
        Args:
            category: Rating category (e.g., "Response Quality", "Speed")
            score: Score from 1-5
            comments: Optional comments
        
        Returns:
            The rating ID
        """
        with self._lock:
            rating_id = f"rt_{self._next_id}"
            self._next_id += 1
            
            rating = Rating(
                rating_id=rating_id,
                user=self.user,
                category=category,
                score=score,
                comments=comments
            )
            
            self._ratings[rating_id] = rating
            self._save_feedback()
            
            logger.info(f"Rating submitted: {rating_id} - {category}: {score}")
            return rating_id
    
    def submit_suggestion(self, subject: str, message: str, 
                          priority: int = 5) -> str:
        """
        Submit a suggestion for improvement.
        
        Args:
            subject: Short subject/title
            message: Detailed suggestion
            priority: Priority level (0-10)
        
        Returns:
            The feedback ID
        """
        return self.submit_feedback(
            feedback_type=FeedbackType.SUGGESTION,
            subject=subject,
            message=message,
            priority=priority
        )
    
    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """Get a specific feedback item."""
        with self._lock:
            return self._feedback.get(feedback_id)
    
    def list_feedback(self, feedback_type: Optional[FeedbackType] = None,
                     status: Optional[FeedbackStatus] = None) -> List[Feedback]:
        """
        List feedback items, optionally filtered.
        
        Args:
            feedback_type: Filter by type
            status: Filter by status
        
        Returns:
            List of matching feedback items
        """
        with self._lock:
            feedbacks = list(self._feedback.values())
            
            if feedback_type:
                feedbacks = [f for f in feedbacks if f.feedback_type == feedback_type]
            if status:
                feedbacks = [f for f in feedbacks if f.status == status]
            
            return sorted(feedbacks, key=lambda x: x.created_at, reverse=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        with self._lock:
            total_feedback = len(self._feedback)
            total_ratings = len(self._ratings)
            
            # Count by type
            type_counts = {}
            for fb in self._feedback.values():
                type_key = fb.feedback_type.value
                type_counts[type_key] = type_counts.get(type_key, 0) + 1
            
            # Count by status
            status_counts = {}
            for fb in self._feedback.values():
                status_key = fb.status.value
                status_counts[status_key] = status_counts.get(status_key, 0) + 1
            
            # Average rating
            if self._ratings:
                avg_rating = sum(rt.score for rt in self._ratings.values()) / len(self._ratings)
            else:
                avg_rating = 0
            
            # Rating by category
            category_ratings = {}
            for rt in self._ratings.values():
                if rt.category not in category_ratings:
                    category_ratings[rt.category] = []
                category_ratings[rt.category].append(rt.score)
            
            category_avg = {
                cat: sum(scores)/len(scores) 
                for cat, scores in category_ratings.items()
            }
            
            return {
                "total_feedback": total_feedback,
                "total_ratings": total_ratings,
                "by_type": type_counts,
                "by_status": status_counts,
                "avg_rating": avg_rating,
                "category_avg_ratings": category_avg,
                "recent_feedback": [fb.to_dict() for fb in self.list_feedback()[:5]]
            }
    
    def update_feedback_status(self, feedback_id: str, status: FeedbackStatus,
                              resolution: str = "") -> bool:
        """
        Update the status of a feedback item.
        
        Args:
            feedback_id: The feedback ID to update
            status: New status
            resolution: Resolution description
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if feedback_id not in self._feedback:
                return False
            
            feedback = self._feedback[feedback_id]
            feedback.status = status
            feedback.updated_at = datetime.now().isoformat()
            
            if status == FeedbackStatus.RESOLVED:
                feedback.resolved_at = feedback.updated_at
                feedback.resolution = resolution
            
            self._save_feedback()
            logger.info(f"Feedback {feedback_id} status updated to {status}")
            return True
    
    def delete_feedback(self, feedback_id: str) -> bool:
        """Delete a feedback item."""
        with self._lock:
            if feedback_id in self._feedback:
                del self._feedback[feedback_id]
                self._save_feedback()
                logger.info(f"Feedback {feedback_id} deleted")
                return True
            return False
    
    def clear_all_feedback(self) -> int:
        """Clear all feedback."""
        with self._lock:
            count = len(self._feedback)
            self._feedback.clear()
            self._ratings.clear()
            self._save_feedback()
            logger.info(f"Cleared {count} feedback items")
            return count
    
    def get_feedback_trends(self) -> Dict[str, Any]:
        """Analyze feedback for trends."""
        with self._lock:
            # Count feedback by day
            by_day = {}
            for fb in self._feedback.values():
                day = fb.created_at[:10]  # YYYY-MM-DD
                by_day[day] = by_day.get(day, 0) + 1
            
            # Count by type and day
            by_type_day = {}
            for fb in self._feedback.values():
                day = fb.created_at[:10]
                type_key = fb.feedback_type.value
                if type_key not in by_type_day:
                    by_type_day[type_key] = {}
                by_type_day[type_key][day] = by_type_day[type_key].get(day, 0) + 1
            
            # Common keywords
            keywords = {}
            for fb in self._feedback.values():
                words = fb.subject.lower().split() + fb.message.lower().split()
                for word in words:
                    if len(word) > 3:  # Skip short words
                        keywords[word] = keywords.get(word, 0) + 1
            
            # Sort keywords by frequency
            sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "by_day": by_day,
                "by_type_day": by_type_day,
                "common_keywords": dict(sorted_keywords)
            }


class FeedbackGUI:
    """
    GUI component for feedback collection.
    
    This provides the UI for:
    - Submitting feedback
    - Rating system performance
    - Viewing feedback history
    """
    
    def __init__(self, parent, feedback_manager: FeedbackManager):
        self.parent = parent
        self.manager = feedback_manager
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the feedback widgets."""
        # This would be integrated into the main dashboard
        pass
    
    def show_feedback_form(self):
        """Show the feedback form dialog."""
        # Implementation would use tkinter dialog
        pass
    
    def show_rating_form(self):
        """Show the rating form dialog."""
        # Implementation would use tkinter dialog
        pass


# Global feedback manager
_global_feedback_manager = None


def get_feedback_manager(user: str = "anonymous") -> FeedbackManager:
    """Get or create the global feedback manager."""
    global _global_feedback_manager
    if _global_feedback_manager is None:
        _global_feedback_manager = FeedbackManager(user=user)
    return _global_feedback_manager


if __name__ == "__main__":
    # Demo usage
    logger.info("Starting feedback manager demo...")
    
    # Create manager
    manager = get_feedback_manager(user="test_user")
    
    # Submit some feedback
    fb1 = manager.submit_feedback(
        feedback_type=FeedbackType.BUG,
        subject="Dashboard not loading",
        message="The dashboard takes too long to load on startup.",
        priority=7
    )
    
    fb2 = manager.submit_suggestion(
        subject="Add dark mode",
        message="Please add a dark mode theme option.",
        priority=5
    )
    
    # Submit ratings
    manager.submit_rating("Response Quality", 4, "Generally good but sometimes slow")
    manager.submit_rating("Speed", 3, "Could be faster")
    manager.submit_rating("Reliability", 5, "Very reliable")
    
    # Get statistics
    stats = manager.get_statistics()
    print("Feedback Statistics:")
    print(f"  Total Feedback: {stats['total_feedback']}")
    print(f"  Total Ratings: {stats['total_ratings']}")
    print(f"  By Type: {stats['by_type']}")
    print(f"  By Status: {stats['by_status']}")
    print(f"  Average Rating: {stats['avg_rating']:.2f}")
    print(f"  Category Averages: {stats['category_avg_ratings']}")
    
    # List feedback
    print("\nRecent Feedback:")
    for fb in manager.list_feedback()[:3]:
        print(f"  - {fb.subject} ({fb.feedback_type.value}): {fb.message[:50]}...")
    
    # Update status
    manager.update_feedback_status(fb1, FeedbackStatus.IN_PROGRESS, "Investigating")
    manager.update_feedback_status(fb2, FeedbackStatus.REVIEWED)
    
    # Get trends
    trends = manager.get_feedback_trends()
    print("\nFeedback Trends:")
    print(f"  By Day: {trends['by_day']}")
    print(f"  Common Keywords: {trends['common_keywords']}")
    
    logger.info("Demo completed")
