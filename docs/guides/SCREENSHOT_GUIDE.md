# 📸 Screenshot Guide for GitHub Documentation

This guide helps you capture the perfect screenshots to showcase LifeLearners.org.nz on GitHub.

## 🎯 Screenshots Needed

### 1. Homepage - Welcoming Community Hub
**URL**: `http://localhost:8000/`
**Key Elements to Capture**:
- Hero section with blue gradient background
- "Discover Your Next Learning Adventure" headline
- Featured upcoming events grid
- Clear call-to-action buttons
- Navigation header with LifeLearners branding

**Recommended Size**: 1200x800px
**Tips**: 
- Capture full page or crop to show hero + first few events
- Make sure the events show diverse types (workshops, field trips, etc.)

### 2. Interactive Events Map
**URL**: `http://localhost:8000/events` (click "🗺️ Map View")
**Key Elements to Capture**:
- Map view with New Zealand visible
- Event markers (green for free, red for paid)
- Marker clustering in action
- Open popup showing event details
- View toggle buttons (List/Map)

**Recommended Size**: 1200x800px
**Tips**:
- Zoom to show multiple regions (Auckland, Wellington, Christchurch)
- Click a marker to show the popup for the screenshot
- Use browser dev tools to make window exactly 1200px wide

### 3. Event Discovery & Booking
**URL**: `http://localhost:8000/events` (List View)
**Key Elements to Capture**:
- Event filter buttons at top
- Beautiful event cards with pricing
- Mix of free and paid events
- "Featured Event" highlight section
- Mobile-responsive grid layout

**Recommended Size**: 1200x1000px (taller to show multiple events)
**Tips**:
- Scroll to show a good variety of events
- Make sure pricing is visible ($0 for free, $25.00 for paid)

### 4. Multi-Child Booking System
**URL**: `http://localhost:8000/event/[any-event-id]/book`
**Key Elements to Capture**:
- Multiple children selection checkboxes
- Allergy/dietary requirements section
- Clear pricing breakdown
- "Book Event" button
- Professional form styling

**Recommended Size**: 1000x800px
**Tips**:
- Login first as a parent with multiple children
- Select 2-3 children to show the multi-child functionality
- Scroll to show allergy management section

### 5. Admin Dashboard
**URL**: `http://localhost:8000/admin`
**Key Elements to Capture**:
- Revenue analytics charts
- Event statistics cards
- Calendar view with events
- Clean, professional admin interface
- Recent bookings table

**Recommended Size**: 1400x900px (wider for dashboard)
**Tips**:
- Login as admin user (admin@example.com / adminpass123)
- Make sure test data is loaded for realistic charts

### 6. Payment Integration
**URL**: During checkout flow
**Key Elements to Capture**:
- Stripe payment form
- Secure payment indicators
- Clear pricing and event details
- Professional checkout interface

**Recommended Size**: 800x1000px
**Tips**:
- Use Stripe test card numbers (4242 4242 4242 4242)
- Capture the secure payment form
- Show the LifeLearners branding in Stripe checkout

## 🛠️ Technical Setup for Screenshots

### Browser Setup
```bash
# Start the application
docker-compose up -d

# Generate test data (if not already done)
docker-compose exec web python scripts/generate_test_data.py
```

### Recommended Tools
- **Chrome DevTools**: Set device to "Desktop" with 1200px width
- **Firefox Screenshots**: Built-in screenshot tool
- **macOS**: Cmd+Shift+4 for region selection
- **Windows**: Snipping Tool or Win+Shift+S
- **Linux**: gnome-screenshot or spectacle

### Browser Settings for Best Screenshots
1. **Zoom**: Set to 100% (Cmd/Ctrl + 0)
2. **Window Width**: 1200-1400px for desktop shots
3. **Hide Bookmarks**: Clean interface
4. **Full Screen**: F11 for immersive shots (optional)

## 📝 Screenshot Naming Convention

Save screenshots with descriptive names:
- `homepage-hero-section.png`
- `events-map-view-with-popup.png`
- `events-list-view-filters.png`
- `multi-child-booking-form.png`
- `admin-dashboard-analytics.png`
- `stripe-payment-checkout.png`

## 🎨 Post-Processing Tips

### Optional Enhancements
- **Add subtle drop shadows** for floating effect
- **Crop carefully** to remove browser chrome
- **Resize to consistent widths** (1200px recommended)
- **Compress for web** using tools like TinyPNG
- **Add device frames** using tools like Mockuphone (optional)

### File Format
- **PNG**: Best for UI screenshots (lossless)
- **WebP**: Smaller file size for web (if supported)
- Keep file sizes under 500KB for GitHub

## 📂 Updating README

Once screenshots are captured:

1. **Upload to repository**: Create `docs/screenshots/` folder
2. **Update README.md**: Replace placeholder text with actual images:
```markdown
### Homepage - Welcoming Community Hub
![Homepage](docs/screenshots/homepage-hero-section.png)

### Interactive Events Map
![Events Map](docs/screenshots/events-map-view-with-popup.png)
```

## 🚀 Pro Tips

### For Marketing/Investor Presentations
- **Capture with realistic data**: Use the generated test data
- **Show activity**: Multiple bookings, recent payments
- **Highlight key features**: Map markers, multi-child selection
- **Mobile shots**: Capture responsive design on phone width

### For Technical Documentation
- **Show admin features**: Dashboard analytics, event management
- **Developer-friendly**: Code examples, API responses
- **Architecture diagrams**: Use tools like draw.io

---

**Goal**: Showcase LifeLearners as a professional, feature-rich platform that's ready for national scale! 🎓✨ 