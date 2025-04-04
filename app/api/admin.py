"""Admin endpoints for monitoring and management"""
from flask import Blueprint, jsonify
from app.services.protection import get_protection_stats

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/stats', methods=['GET'])
def admin_stats():
    """Show current DDoS protection statistics"""
    return jsonify(get_protection_stats()), 200
