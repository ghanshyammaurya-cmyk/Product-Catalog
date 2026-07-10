"""Centralized selectors for builders.intel.com Edge AI Catalog."""

COOKIE_ACCEPT_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button:has-text('Accept All')",
    "button:has-text('Accept')",
]

GLOBAL_SEARCH_SELECTORS = ["input#mobile-search", "input[name='igq']"]

CATALOG_SEARCH_SELECTORS = [
    "input#pSearch",
    "input[name='pSearch']",
    "input[placeholder*='Search Products' i]",
]

MAIN_MENU_SELECTORS = {
    "engagement": [
        "a[href*='engagement' i]:visible",
        "nav >> text=Engagement",
        "[class*='nav' i] >> text=Engagement",
    ],
    "solution_hub": [
        "a:has-text('Solution Hub')",
        "a[href*='solution-hub' i]",
    ],
    "edge_ai_catalog": [
        "a:has-text('Edge AI Catalog')",
        "a[href*='edge-ai-catalog' i]:not([href*='partner-spotlight'])",
    ],
}

EXPLORE_PARTNER_SPOTLIGHT_SELECTORS = [
    "a:has-text('Explore Partner Spotlight')",
    "a[href*='/partner-spotlight']:has-text('Explore')",
]

PARTNER_DROPDOWN_SELECTORS = [
    "select#ecosystemPartner",
    "select[name*='partner' i]",
    "select[id*='partner' i]",
    "[class*='partner' i] select",
]

PARTNER_DROPDOWN_TRIGGERS = [
    "button:has-text('Filter By Partners')",
    ".multiselect-native-select button.dropdown-toggle",
    ".multiselect button.dropdown-toggle",
    "button.dropdown-toggle:has(+ .multiselect-container)",
]

PARTNER_DROPDOWN_SEARCH_INPUTS = [
    ".multiselect-container input[type='text']",
    ".multiselect-filter input",
    ".dropdown-menu input[type='text']",
]

CATALOG_COUNT_SELECTORS = [
    "h2:has-text('Unique Products')",
    "h3:has-text('Unique Products')",
    "h4:has-text('Unique Products')",
    "p:has-text('Unique Products')",
    "div:has-text('Unique Products')",
    "span:has-text('Unique Products')",
]

LISTING_TAG_SELECTORS = [
    ".cat-class",
    "[class*='cat-class' i]",
    ".listview [class*='badge' i]",
    ".gridview [class*='badge' i]",
]

QUICK_VIEW_OVERLAY_SELECTORS = [
    ".popover",
    "[class*='popover' i]",
    "[class*='quick-view' i]",
    "[role='tooltip']",
]

VIEW_MORE_SELECTORS = [
    "a:has-text('View More')",
    "button:has-text('View More')",
]

PRODUCT_TYPE_SELECTORS = {
    "system": [
        "text=Edge AI System",
        "a:has-text('Edge AI System')",
        "[class*='sidebar' i] >> text=Edge AI System",
        "aside >> text=Edge AI System",
    ],
    "application": [
        "text=Edge AI Application",
        "a:has-text('Edge AI Application')",
        "[class*='sidebar' i] >> text=Edge AI Application",
        "aside >> text=Edge AI Application",
    ],
}

BREADCRUMB_SELECTORS = [".breadcrumb", "[class*='breadcrumb' i]:not(nav ol)"]

GRID_VIEW_SELECTORS = [
    "button.btn-primary.mask-pii:has(i.fa-th-large)",
    "button.btn:has(i.fa-th-large):not([class*='category-host'])",
    "button:has(i.fa-th-large)",
]
LIST_VIEW_SELECTORS = [
    "button.btn-primary.mask-pii:has(i.fa-th-list)",
    "button.btn:has(i.fa-th-list):not([class*='category-host'])",
    "button:has(i.fa-th-list)",
]

LISTING_CARD_SELECTOR = ".listview, .gridview"
PRODUCT_LINK_SELECTORS = [
    "a[href*='/partner-spotlight/'][href*='-']",
    "a:has-text('Product Details')",
]
QUICK_VIEW_SELECTORS = ["a.quick-view", "a:has-text('Quick View')", "a.listview-quick-view"]

PARTNER_LOGO_LISTING_SELECTORS = ["img[src*='companyLogo' i]", "img[src*='images/company' i]"]
PARTNER_LOGO_SELECTORS = PARTNER_LOGO_LISTING_SELECTORS + ["[class*='product' i] img", "[class*='partner' i] img"]
THUMBNAIL_SELECTORS = ["img[src*='productImage' i]", "img[src*='catalog/large' i]"]

PRODUCT_TITLE_SELECTORS = [
    "h2:not(:has-text('Filter By')):not(:has-text('Subscribe')):not(:has-text('Oops'))",
]

CONTACT_LINK_SELECTORS = [
    "a:has-text('Contact')",
    "a:has-text('Partner Contact')",
    "button:has-text('Contact')",
    "button:has-text('Partner Contact')",
    "a[href*='contact' i]",
    "a[href*='mailto:' i]",
    "[class*='contact' i] a",
    "[class*='contact' i] button",
]

FEATURES_SECTION_SELECTORS = [
    "[class*='feature' i]",
    "h2:has-text('Features')",
    "h3:has-text('Features')",
]

RESOURCES_SECTION_SELECTORS = [
    "[class*='resource' i] a",
    "a.trackpdfdwload",
    "a:has-text('Download')",
    "a[href$='.pdf']",
]
RESOURCE_LINK_SELECTORS = RESOURCES_SECTION_SELECTORS + [
    "a:has-text('Product Details')",
    "a:has-text('Quick View')",
    "a:has-text('Read more')",
    "a[href*='partner-spotlight']",
]

CATEGORIES_SECTION_SELECTORS = [
    "[class*='categor' i]",
    "h2:has-text('Categories')",
    "h3:has-text('Categories')",
]

RELATED_PRODUCTS_SELECTORS = [
    "h2:has-text('Related Products')",
    "[class*='related' i]",
]

METADATA_SELECTORS = {
    "title": "title",
    "description": "meta[name='description']",
    "keywords": "meta[name='keywords']",
    "og_title": "meta[property='og:title']",
    "og_description": "meta[property='og:description']",
    "canonical": "link[rel='canonical']",
}

PDF_LINK_SELECTORS = [
    "a:has-text('Download Offline Systems Catalog')",
    "a:has-text('Download Offline Applications Catalog')",
    "a.trackpdfdwload",
    "a[href$='.pdf']",
]
