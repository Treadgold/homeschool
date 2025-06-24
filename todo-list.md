# TODO List for Homeschool Event Booking System

## High Priority
- [x] Add user profile page (view/update email, password)
- [x] Add user profile route and template
- [x] Add link to profile page in site navigation/header when logged in.
- [x] Implement event booking and cancellation for parents
- [x] Multi-child booking support
- [x] Create custom event booking page for parents with dynamic add-child UI
- [x] Add Child model and migration
- [x] Add Booking model and migration
- [x] Add /event/{event_id}/book route and template
- [x] Add dynamic 'add child' UI (JS)
- [x] Add backend logic for booking/cancellation
- [x] Show bookings on profile page
- [ ] Add email notifications for signup, booking, and admin actions
- [ ] Improve error handling and user feedback on forms
- [ ] Add automated tests (pytest)

## Medium Priority
- [ ] Waitlist for full events
- [ ] Admin dashboard with event stats and charts
- [ ] Export event data as CSV
- [ ] Add Stripe payment integration for paid events
- [ ] Add calendar/date-picker UI for event creation

## Low Priority
- [ ] SMS reminders (Twilio)
- [ ] Self-check-in for events
- [ ] Google Calendar/ICS export
- [ ] Accessibility improvements (a11y)

## Code Quality & DevOps
- [ ] Add pre-commit hooks (Black, Ruff, MyPy)
- [ ] Add CI pipeline for tests and linting
- [ ] Improve documentation (code comments, API docs)
- [ ] Refactor to use service/repository patterns as needed 