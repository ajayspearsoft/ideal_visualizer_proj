from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import time

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Mock Data
rooms = [
    {
        'id': 'living-room',
        'name': 'Living Room',
        'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=600&h=400&fit=crop',
        'description': 'Explore wall and floor options for your living space',
    },
    {
        'id': 'bedroom',
        'name': 'Bedroom',
        'image': 'https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=600&h=400&fit=crop',
        'description': 'Design your perfect bedroom retreat',
    },
    {
        'id': 'kitchen',
        'name': 'Kitchen',
        'image': 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=400&fit=crop',
        'description': 'Visualize countertops, backsplash and flooring',
    },
    {
        'id': 'bathroom',
        'name': 'Bathroom',
        'image': 'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=600&h=400&fit=crop',
        'description': 'Preview tiles, walls and flooring for your bathroom',
    },
    {
        'id': 'dining-room',
        'name': 'Dining Room',
        'image': 'https://images.unsplash.com/photo-1617806118233-18e1de247200?w=600&h=400&fit=crop',
        'description': 'Find the ideal look for your dining area',
    },
    {
        'id': 'hallway',
        'name': 'Hallway / Entryway',
        'image': 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=600&h=400&fit=crop',
        'description': 'Make a great first impression with the right finishes',
    },
    {
        'id': 'office',
        'name': 'Home Office',
        'image': 'https://images.unsplash.com/photo-1593062096033-9a26b09da705?w=600&h=400&fit=crop',
        'description': 'Create a productive and inspiring workspace',
    },
    {
        'id': 'laundry',
        'name': 'Laundry Room',
        'image': 'https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?w=600&h=400&fit=crop',
        'description': 'Durable and stylish options for utility spaces',
    },
]

products = [
    # Marbles
    {'id': 1, 'name': 'Calacatta Gold Marble', 'type': 'wall', 'color': '#f8f8f8', 'preview': 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1000&q=80'},
    {'id': 2, 'name': 'Black Marquina Marble', 'type': 'wall', 'color': '#1a1a1a', 'preview': 'https://images.unsplash.com/photo-1504198453319-5ce911bafcde?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1504198453319-5ce911bafcde?w=1000&q=80'},
    {'id': 3, 'name': 'Emerald Green Marble', 'type': 'wall', 'color': '#1b4d3e', 'preview': 'https://images.unsplash.com/photo-1615529328331-f8917597711f?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1615529328331-f8917597711f?w=1000&q=80'},
    
    # Colorful Wallpapers
    {'id': 4, 'name': 'Tropical Floral Design', 'type': 'wall', 'color': '#ffcc00', 'preview': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=1000&q=80'},
    {'id': 5, 'name': 'Abstract Geometric Color', 'type': 'wall', 'color': '#3498db', 'preview': 'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=1000&q=80'},
    {'id': 6, 'name': 'Vintage Royal Gold', 'type': 'wall', 'color': '#d4af37', 'preview': 'https://images.unsplash.com/photo-1614850523296-d8c1af93d400?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1614850523296-d8c1af93d400?w=1000&q=80'},
    {'id': 7, 'name': 'Modern Art Blue', 'type': 'wall', 'color': '#2980b9', 'preview': 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1000&q=80'},
    
    # Flooring
    {'id': 8, 'name': 'Polished Oak Floor', 'type': 'floor', 'color': '#b8956a', 'preview': 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=1000&q=80'},
    {'id': 9, 'name': 'White Ceramic Tile', 'type': 'floor', 'color': '#ffffff', 'preview': 'https://images.unsplash.com/photo-1600607687644-c7171b42498f?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1600607687644-c7171b42498f?w=1000&q=80'},
    {'id': 10, 'name': 'Slate Gray Stone', 'type': 'floor', 'color': '#2c3e50', 'preview': 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=200&h=200&fit=crop', 'pattern': 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=1000&q=80'},
]

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    return jsonify(rooms)

@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(products)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = f"{int(time.time())}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_url = f"http://localhost:5000/uploads/{filename}"
        return jsonify({'imageUrl': image_url})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
