document.addEventListener('DOMContentLoaded', function() {
    const hamburgerMenu = document.getElementById('hamburger-menu');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const logoutLink = document.getElementById('logout-link');
    const sidebarLinks = sidebar.querySelectorAll('a[data-route]'); // Select links with data-route attribute

    // Function to toggle sidebar visibility
    function toggleSidebar() {
        sidebar.classList.toggle('active');
        mainContent.classList.toggle('shifted');
    }

    // Event listener for hamburger menu click
    if (hamburgerMenu) {
        hamburgerMenu.addEventListener('click', toggleSidebar);
    }

    // Event listener for logout confirmation
    if (logoutLink) {
        logoutLink.addEventListener('click', function(event) {
            // Prevent default link behavior
            event.preventDefault();
            // Show confirmation dialog
            if (window.confirm('Are you sure you want to log out?')) {
                // If confirmed, navigate to the logout URL
                window.location.href = this.href;
            }
        });
    }

    // Function to highlight the active sidebar link
    function highlightActiveLink() {
        const currentPath = window.location.pathname; // Get current URL path (e.g., /admin_dashboard)

        sidebarLinks.forEach(link => {
            // Remove active class from all links first
            link.classList.remove('active');

            // Get the route name from data-route attribute
            const routeName = link.getAttribute('data-route');
            // Construct the expected URL for this route
            // For example, if routeName is 'admin_dashboard', expectedUrl is '/admin_dashboard'
            const expectedUrl = '/' + routeName.replace(/_/g, '-'); // Replace underscores with hyphens for URL consistency

            // Check if the current path matches the expected URL for this link
            if (currentPath === expectedUrl) {
                link.classList.add('active'); // Add active class if it's the current page
            }
            // Special case for the root '/' mapping to admin_dashboard or login
            if (currentPath === '/' && routeName === 'admin_dashboard') {
                link.classList.add('active');
            }
        });
    }

    // Call highlight function on page load
    highlightActiveLink();

    // Close sidebar if clicking outside when it's open (for larger screens)
    mainContent.addEventListener('click', function() {
        if (sidebar.classList.contains('active') && window.innerWidth > 768) {
            toggleSidebar();
        }
    });

    // Prevent main content click from closing sidebar on hamburger menu click itself
    hamburgerMenu.addEventListener('click', function(event) {
        event.stopPropagation();
    });

    // Optional: Close sidebar when a sidebar link is clicked (useful for mobile)
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (sidebar.classList.contains('active') && window.innerWidth <= 768) {
                toggleSidebar();
            }
        });
    });
});
