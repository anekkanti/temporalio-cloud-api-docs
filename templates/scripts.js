// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Highlight active navigation item based on scroll position
function updateActiveNav() {
    const sections = document.querySelectorAll('h2[id], h3[id]');
    const navLinks = document.querySelectorAll('.nav-link, .nav-sublink');
    
    let currentSection = '';
    
    sections.forEach(section => {
        const rect = section.getBoundingClientRect();
        if (rect.top <= 100 && rect.bottom >= 100) {
            currentSection = section.id;
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + currentSection) {
            link.classList.add('active');
        }
    });
}

window.addEventListener('scroll', updateActiveNav);
updateActiveNav(); // Initial call 

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    
    if (!searchInput || !searchResults) return;
    
    let allNavItems = [];
    
    // Collect all navigation items
    function collectNavItems() {
        allNavItems = [];
        
        // Collect services and their methods
        document.querySelectorAll('.nav-item').forEach(serviceItem => {
            const serviceLink = serviceItem.querySelector('.nav-link');
            if (serviceLink) {
                const serviceName = serviceLink.textContent.trim();
                allNavItems.push({
                    element: serviceItem,
                    text: serviceName,
                    type: 'service',
                    link: serviceLink
                });
                
                // Collect methods within this service
                const subList = serviceItem.querySelector('.nav-sublist');
                if (subList) {
                    subList.querySelectorAll('li').forEach(methodItem => {
                        const methodLink = methodItem.querySelector('.nav-sublink');
                        if (methodLink) {
                            const methodName = methodLink.textContent.trim();
                            allNavItems.push({
                                element: methodItem,
                                text: methodName,
                                type: 'method',
                                service: serviceName,
                                link: methodLink
                            });
                        }
                    });
                }
            }
        });
        
        // Collect types
        const allHeaders = document.querySelectorAll('.sidebar h2');
        let typesNavList = null;
        
        allHeaders.forEach(header => {
            if (header.textContent.trim() === 'Types') {
                typesNavList = header.nextElementSibling;
            }
        });
        
        if (typesNavList && typesNavList.classList.contains('nav-list')) {
            typesNavList.querySelectorAll('li').forEach(typeItem => {
                const typeLink = typeItem.querySelector('.nav-sublink');
                if (typeLink) {
                    const typeName = typeLink.textContent.trim();
                    allNavItems.push({
                        element: typeItem,
                        text: typeName,
                        type: 'type',
                        link: typeLink
                    });
                }
            });
        }
    }
    
    // Highlight matching text
    function highlightText(text, searchTerm) {
        if (!searchTerm) return text;
        const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<span class="search-highlight">$1</span>');
    }
    
    // Filter navigation items
    function filterNavItems(searchTerm) {
        searchTerm = searchTerm.toLowerCase().trim();
        
        if (!searchTerm) {
            // Show all items
            allNavItems.forEach(item => {
                item.element.classList.remove('hidden');
                item.link.innerHTML = item.text;
            });
            
            // Show all service containers and sublists
            document.querySelectorAll('.nav-item').forEach(serviceItem => {
                serviceItem.classList.remove('hidden');
                const subList = serviceItem.querySelector('.nav-sublist');
                if (subList) {
                    subList.style.display = 'block';
                }
            });
            
            // Show section headers
            document.querySelectorAll('.sidebar h2').forEach(header => {
                header.style.display = 'block';
            });
            
            searchResults.textContent = '';
            return;
        }
        
        const matchingServices = new Set();
        const servicesWithMatchingMethods = new Set();
        let matchingItems = new Set(); // Only count items that directly match
        
        // First pass: identify matching items and services with matching methods
        allNavItems.forEach(item => {
            const matches = item.text.toLowerCase().includes(searchTerm);
            
            if (matches) {
                matchingItems.add(item.text + '|' + item.type); // Only count direct matches
                if (item.type === 'service') {
                    matchingServices.add(item.text);
                } else if (item.type === 'method' && item.service) {
                    servicesWithMatchingMethods.add(item.service);
                }
            }
        });
        
        // Second pass: apply visibility and highlighting
        allNavItems.forEach(item => {
            const matches = item.text.toLowerCase().includes(searchTerm);
            const shouldShow = matches || 
                (item.type === 'service' && servicesWithMatchingMethods.has(item.text)) ||
                (item.type === 'method' && matchingServices.has(item.service));
            
            if (shouldShow) {
                item.element.classList.remove('hidden');
                if (matches) {
                    item.link.innerHTML = highlightText(item.text, searchTerm);
                } else {
                    item.link.innerHTML = item.text;
                }
            } else {
                item.element.classList.add('hidden');
                item.link.innerHTML = item.text;
            }
        });
        
        // Handle service containers and sublists
        document.querySelectorAll('.nav-item').forEach(serviceItem => {
            const serviceLink = serviceItem.querySelector('.nav-link');
            const serviceName = serviceLink ? serviceLink.textContent.trim() : '';
            const subList = serviceItem.querySelector('.nav-sublist');
            
            const serviceMatches = serviceName.toLowerCase().includes(searchTerm);
            const hasMatchingMethods = servicesWithMatchingMethods.has(serviceName);
            const shouldShowService = serviceMatches || hasMatchingMethods || matchingServices.has(serviceName);
            
            if (shouldShowService) {
                serviceItem.classList.remove('hidden');
                if (subList) {
                    subList.style.display = 'block';
                }
            } else {
                serviceItem.classList.add('hidden');
                if (subList) {
                    subList.style.display = 'none';
                }
            }
        });
        
        // Show/hide section headers based on results
        const hasServiceResults = matchingServices.size > 0 || servicesWithMatchingMethods.size > 0;
        const hasTypeResults = Array.from(allNavItems).some(item => 
            item.type === 'type' && !item.element.classList.contains('hidden')
        );
        
        document.querySelectorAll('.sidebar h2').forEach(header => {
            const headerText = header.textContent.trim();
            if (headerText === 'Services') {
                header.style.display = hasServiceResults ? 'block' : 'none';
            } else if (headerText === 'Types') {
                header.style.display = hasTypeResults ? 'block' : 'none';
            }
        });
        
        // Show search results
        const matchingCount = matchingItems.size;
        if (matchingCount === 0) {
            searchResults.textContent = 'No results found';
        } else {
            searchResults.textContent = `${matchingCount} result${matchingCount === 1 ? '' : 's'} found`;
        }
    }
    
    // Initialize
    collectNavItems();
    
    // Add search event listener
    searchInput.addEventListener('input', (e) => {
        filterNavItems(e.target.value);
    });
    
    // Clear search on escape
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            searchInput.value = '';
            filterNavItems('');
            searchInput.blur();
        }
    });
}

// Copy link to clipboard functionality
function copyLinkToClipboard(anchor, button) {
    const currentUrl = window.location.href.split('#')[0];
    const fullUrl = currentUrl + '#' + anchor;
    
    navigator.clipboard.writeText(fullUrl).then(() => {
        // Show success feedback
        const originalText = button.textContent;
        button.textContent = '✓';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = fullUrl;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            const originalText = button.textContent;
            button.textContent = '✓';
            button.classList.add('copied');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
        } catch (err) {
            console.error('Failed to copy link: ', err);
        }
        document.body.removeChild(textArea);
    });
}

// Initialize link buttons when DOM is loaded
function initializeLinkButtons() {
    document.querySelectorAll('.link-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const anchor = button.getAttribute('data-anchor');
            
            // Update the URL to include the anchor
            window.history.pushState(null, null, '#' + anchor);
            
            // Copy link to clipboard
            copyLinkToClipboard(anchor, button);
            
            // Scroll to move the target element to the top of the page
            const targetElement = document.getElementById(anchor);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Tab functionality
function initializeTabs() {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (e) => {
            const targetTabId = button.getAttribute('data-tab');
            const tabContainer = button.closest('.tab-container');
            
            // Remove active class from all buttons and panes in this container
            tabContainer.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            tabContainer.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button and corresponding pane
            button.classList.add('active');
            const targetPane = document.getElementById(targetTabId);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });
}

// Initialize search when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeSearch();
    initializeLinkButtons();
    initializeTabs();
});