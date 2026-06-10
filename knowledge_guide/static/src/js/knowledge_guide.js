/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

/**
 * Knowledge Guide - Client Action OWL
 *
 * Main interface for the knowledge guide with a navigation sidebar
 * and a reading area rendering the HTML content of pages.
 */
class KnowledgeGuide extends Component {
    static template = "knowledge_guide.MainTemplate";

    setup() {
        this.state = useState({
            pages: [],
            categories: [],
            selectedPage: null,
            searchTerm: "",
            loading: true,
            error: false,
            expandedCategories: new Set(),
        });

        onWillStart(async () => {
            await this.loadPages();
        });

        onMounted(() => {
            // Auto-select the first page on initial load when available
            if (this.state.pages.length > 0 && !this.state.selectedPage) {
                this.selectPage(this.state.pages[0]);
            }
        });
    }

    async loadPages(searchTerm = "") {
        try {
            this.state.loading = true;
            this.state.error = false;

            const result = await rpc("/knowledge_guide/get_pages", {
                search_term: searchTerm || undefined,
            });

            this.state.pages = result.pages.map((p) => ({
                ...p,
                content_html: markup(p.content_html || ""),
            }));
            this.state.categories = result.categories;
            this.state.loading = false;

            // When searching, do not auto-select.
            // If the currently selected page disappears, reset selection.
            if (searchTerm && this.state.selectedPage) {
                const pageStillExists = this.state.pages.find(
                    (p) => p.id === this.state.selectedPage.id
                );
                if (!pageStillExists) {
                    this.state.selectedPage = null;
                }
            }
        } catch (error) {
            console.error("Error loading knowledge guide pages:", error);
            this.state.error = true;
            this.state.loading = false;
        }
    }

    selectPage(page) {
        this.clearHighlights();

        this.state.selectedPage = page;

        if (page && page.category) {
            this.state.expandedCategories.add(page.category);
        }

        setTimeout(() => {
            if (this.state.searchTerm) {
                this.highlightSearchTerm(this.state.searchTerm);
            }
        }, 50);
    }

    onSearchInput(ev) {
        const searchTerm = ev.target.value;
        this.state.searchTerm = searchTerm;

        // 300ms debounce
        clearTimeout(this._searchTimeout);
        this._searchTimeout = setTimeout(() => {
            this.loadPages(searchTerm);
        }, 300);
    }

    getPagesByCategory(category) {
        return this.state.pages.filter((p) => p.category === category);
    }

    isPageSelected(page) {
        return this.state.selectedPage && this.state.selectedPage.id === page.id;
    }

    toggleCategory(category) {
        if (this.state.expandedCategories.has(category)) {
            this.state.expandedCategories.delete(category);
        } else {
            this.state.expandedCategories.add(category);
        }
        this.state.expandedCategories = new Set(this.state.expandedCategories);
    }

    isCategoryExpanded(category) {
        return this.state.expandedCategories.has(category);
    }

    /**
     * Highlight all occurrences of the search term in the content area.
     */
    highlightSearchTerm(searchTerm) {
        if (!searchTerm || searchTerm.length < 2) {
            return;
        }

        const contentArea = document.querySelector('.user-guide-content');
        if (!contentArea) {
            return;
        }

        const escapedTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(escapedTerm, 'gi');

        const walker = document.createTreeWalker(
            contentArea,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: (node) => {
                    const parent = node.parentElement;
                    if (!parent ||
                        parent.tagName === 'SCRIPT' ||
                        parent.tagName === 'STYLE' ||
                        parent.classList.contains('search-highlight')) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    return regex.test(node.textContent)
                        ? NodeFilter.FILTER_ACCEPT
                        : NodeFilter.FILTER_REJECT;
                }
            }
        );

        const nodesToProcess = [];
        let currentNode;
        while (currentNode = walker.nextNode()) {
            nodesToProcess.push(currentNode);
        }

        let firstHighlight = null;

        nodesToProcess.forEach(textNode => {
            const parent = textNode.parentElement;
            const text = textNode.textContent;
            const fragment = document.createDocumentFragment();
            let lastIndex = 0;
            let match;

            regex.lastIndex = 0;

            while ((match = regex.exec(text)) !== null) {
                if (match.index > lastIndex) {
                    fragment.appendChild(
                        document.createTextNode(text.substring(lastIndex, match.index))
                    );
                }

                const mark = document.createElement('mark');
                mark.className = 'search-highlight';
                mark.textContent = match[0];
                fragment.appendChild(mark);

                if (!firstHighlight) {
                    firstHighlight = mark;
                }

                lastIndex = regex.lastIndex;
            }

            if (lastIndex < text.length) {
                fragment.appendChild(
                    document.createTextNode(text.substring(lastIndex))
                );
            }

            parent.replaceChild(fragment, textNode);
        });

        if (firstHighlight) {
            setTimeout(() => {
                firstHighlight.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }, 100);
        }
    }

    clearHighlights() {
        const highlights = document.querySelectorAll('.search-highlight');
        highlights.forEach(mark => {
            const parent = mark.parentNode;
            const textNode = document.createTextNode(mark.textContent);
            parent.replaceChild(textNode, mark);
            parent.normalize();
        });
    }
}

registry.category("actions").add("knowledge_guide.main", KnowledgeGuide);

export default KnowledgeGuide;
