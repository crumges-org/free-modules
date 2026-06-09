/** @odoo-module **/

import { Component, useRef, onMounted, useState, markup  } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { useDebounced } from "@web/core/utils/timing";
import { rpc as jsonRpc } from "@web/core/network/rpc";
import { session } from "@web/session";

export class KnowledgeSplit extends Component {
    static template = "i8_knowledge_management.KnowledgeSplit";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.root = useRef("root-template");
        this.splitter = useRef("splitter");
        this.cardPanel = useRef("cardPanel");
        this.cardToggleIcon = useRef("cardToggleIcon");

        this.debouncedSearch = useDebounced(this._performSearch.bind(this), 300);

        this.articles = [];
        this.filteredArticles = [];
        this.currentArticle = null;
        this.searching = false;
        this.tagMatchedIds = new Set();
        this.viewedArticles = new Set(
            JSON.parse(sessionStorage.getItem("viewedArticles") || "[]")
        );
        this.partnerIdPromise = this._getPartnerId();
        this.userCache = new Map();
        this.articleContentCache = new Map();

        this.state = useState({
            isFollowing: false,
            commentLoading: false,
            currentArticleName: null,
            showSearchPanel: false,
            searchResults: [],
            onlyFavorites: false,
            favoriteMap: {},
            showMoreOptions: false,
            showMetadata: false,
            createdBy: '',
            createdByAvatar: '',
            createdOn: '',
            modifiedBy: '',
            modifiedByAvatar: '',
            modifiedOn: '',
            selectedTags: [],
            availableTags: [],
            showDropdown: false,
            showRenameModal: false,
            renameTitle: '',
            showMoveModal: false,
            moveTargetId: null,
            selectedMoveTarget: null,
            breadcrumbHtml: '',
            collapsedNodes: new Set(),
            showArchived: false,
            showArchiveModal: false,
            showUnarchiveModal: false,
            canArchive: false,
            canUnarchive: false,
            isActive: true,
            showNewArticlePanel: false,
            newArticleTitle: "",
            creatingArticle: false,
            showCopyModal: false,
            copyTitle: '',
            showTagModal: false,
            selectedTagIds: [],
            tagSearch: '',
            versionHistory: [],
            showVersionHistoryPanel: false,
            showDiffPanel: false,
            diffHtml: '',
            oldVersionId: null,
            currentVersionId: null,
            compareSourceVersionId: null,
            compareTargetVersionId: null,
            viewsCount: 0,
            likesCount: 0,
            likedByIds: [],
            sortOrder: "name",
            searchInContent: localStorage.getItem("search_in_content") === "1",
            sidebarCollapsed: false,
        });

        onMounted(() => this._onMounted());
    }

    async _onMounted() {
        this._restorePersistedState();
        this._initStickyToolbar();

        const partnerIdPromise = this.partnerIdPromise || this._getPartnerId();
        const tagsPromise = this.orm.searchRead("knowledge.tag", [], ["id", "name"]);
        const articlesPromise = this.orm.searchRead(
            "knowledge.article",
            [["is_published", "=", true]],
            ["id","name","parent_id","tag_ids","active","display_name","views_count","likes_count","liked_by_ids","create_date","write_date","create_uid","write_uid","share_token"],
            { context: { active_test: false } }
        );
        const followersPromise = partnerIdPromise.then((partnerId) =>
            this.orm.searchRead("mail.followers",
                [["res_model","=","knowledge.article"],["partner_id","=",partnerId]],
                ["res_id"]
            )
        );

        const [tags, allRecords, followerRecords] = await Promise.all([tagsPromise, articlesPromise, followersPromise]);

        this.state.availableTags = tags;
        this.tagIdToName = new Map(tags.map(t => [t.id, t.name]));

        const favMap = {};
        for (const r of followerRecords) favMap[r.res_id] = true;
        this.state.favoriteMap = favMap;

        const tagName = (id) => this.tagIdToName.get(id) || "";
        const enriched = allRecords.map(r => ({
            ...r,
            parent_id: r.parent_id ? r.parent_id[0] : null,
            tag_ids_raw: r.tag_ids,
            tag_ids: (r.tag_ids || []).map(tagName),
            expanded: true,
        }));
        this.allArticles = enriched;
        this.articles = enriched;

        const hashParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
        const deepLinkedId = parseInt(hashParams.get('article_id'));
        let initialArticle = !isNaN(deepLinkedId) ? this.allArticles.find(a => a.id === deepLinkedId) : null;
        if (!initialArticle && this.lastSelectedArticleId) {
            initialArticle = this.articles.find(a => a.id === this.lastSelectedArticleId);
        }
        this.filterArticles();
        this.renderArticle(initialArticle || this.articles[0]);

        this._initSplitter();
        this._bindUI();

        this._boundGlobalClick = this._onGlobalClick.bind(this);
        this._boundEscape = this._onEscapeKey.bind(this);
        this._boundBreadcrumb = this.handleBreadcrumbClick.bind(this);

        document.addEventListener("click", this._boundGlobalClick, { passive: true });
        document.addEventListener("keydown", this._boundEscape);
        document.addEventListener("click", this._boundBreadcrumb, { passive: true });

        this._boundCleanup = () => {
            document.removeEventListener("click", this._boundGlobalClick);
            document.removeEventListener("keydown", this._boundEscape);
            document.removeEventListener("click", this._boundBreadcrumb);
            window.removeEventListener("beforeunload", this._boundCleanup);
        };
        window.addEventListener("beforeunload", this._boundCleanup, { once: true });

        this._newArticleAutoFocus();
        this._saveOnEnter();
        this.root.el.querySelector(".o_article_list")?.addEventListener("click", this._onTreeToggleClick.bind(this));

        const rootEl = this.root.el;
        if (this.state.sidebarCollapsed) {
            rootEl.classList.add("sidebar-collapsed");
        } else {
            rootEl.classList.remove("sidebar-collapsed");
        }

        const sidebar = this.root.el.querySelector(".o_knowledge_sidebar");
        const savedWidth = parseInt(localStorage.getItem("sidebar_width"), 10);
        if (!isNaN(savedWidth) && savedWidth >= 150 && savedWidth <= 600) {
            sidebar.style.width = savedWidth + "px";
        }
    }

    async loadArticles() {
        const partnerId = await this.partnerIdPromise;

        const [allRecords, followerRecords] = await Promise.all([
            this.orm.searchRead("knowledge.article",
                [["is_published", "=", true]],
                [
                    "id", "name", "parent_id", "tag_ids", "active", "display_name",
                    "views_count", "likes_count", "liked_by_ids",
                    "create_date", "write_date", "create_uid", "write_uid", "share_token"
                ],
                { context: { active_test: false } }
            ),
            this.orm.searchRead("mail.followers",
                [["res_model", "=", "knowledge.article"], ["partner_id", "=", partnerId]],
                ["res_id"]
            ),
        ]);

        const favSet = new Set(followerRecords.map(r => r.res_id));
        const favMap = {};
        for (const id of favSet) favMap[id] = true;
        this.state.favoriteMap = favMap;

        const tagName = (id) => this.tagIdToName?.get(id) || "";

        const enriched = allRecords.map(r => ({
            ...r,
            parent_id: r.parent_id ? r.parent_id[0] : null,
            tag_ids_raw: r.tag_ids,
            tag_ids: (r.tag_ids || []).map(tagName),
            expanded: true,
        }));

        this.allArticles = enriched;
        this.articles = enriched;

        if (!this.currentArticle && !this.lastSelectedArticleId && this.articles.length) {
            setTimeout(() => this.renderArticle(this.articles[0]), 0);
        }

        if (this.state.onlyFavorites || this.state.selectedTags.length) {
            for (const article of this.filteredArticles) {
                let parentId = article.parent_id;
                while (parentId) {
                    const parent = this.articles.find(a => a.id === parentId);
                    if (parent) {
                        parent.expanded = true;
                        parentId = parent.parent_id;
                    } else break;
                }
            }
        }
    }

    _refreshTree(isFiltered = false) {
        const list = this.root.el.querySelector(".o_article_list");
        const source = isFiltered ? this.filteredArticles : this.articles;
        const frag = document.createDocumentFragment();
        list.innerHTML = "";
        if (!source.length) {
            const noMatch = document.createElement("div");
            noMatch.className = "text-muted small px-3 py-2 d-flex align-items-center";
            noMatch.innerHTML = `<i class="fa fa-folder-open me-2"></i> No articles match the current filters.`;
            frag.appendChild(noMatch);
        } else {
            this._renderTree(frag, source);
        }
        list.appendChild(frag);
    }

    _renderTree(container, articles, parentId = null) {
        const children = articles.filter(a => a.parent_id === parentId);
        if (!children.length) return;

        const ul = document.createElement("ul");
        ul.classList.add("tree");

        const q = this.root.el.querySelector(".o_article_search_input")?.value.toLowerCase() || "";

        for (const article of children) {
            const li = document.createElement("li");
            li.dataset.articleId = article.id;
            li.classList.add("tree-item");
            li.classList.toggle("expanded", article.expanded);

            const nodeRow = document.createElement("div");
            nodeRow.classList.add("tree-node");
            if (this.currentArticle?.id === article.id) {
                nodeRow.classList.add("selected-row");
            }
            if (article.isTagMatch) {
                nodeRow.classList.add("tag-highlight");
            }

            const hasChildren = articles.some(a => a.parent_id === article.id);
            const icon = document.createElement("span");

            if (hasChildren) {
                icon.classList.add("tree-toggle-icon");
                icon.innerText = article.expanded ? "▾" : "▸";
                icon.onclick = null;
                icon.addEventListener("click", (e) => {
                    e.stopPropagation();
                    article.expanded = !article.expanded;
                    localStorage.setItem("expanded_nodes", JSON.stringify(
                        this.articles.filter(a => a.expanded).map(a => a.id)
                    ));
                    this._refreshTree(this.isFilteredView);
                });
            } else {
                icon.classList.add("tree-doc-icon");
                icon.innerText = "📄";
            }

            nodeRow.appendChild(icon);

            const label = document.createElement("span");
            label.classList.add("tree-label");
            label.title = article.name;

            const idx = article.name.toLowerCase().indexOf(q);
            if (q && idx !== -1) {
                const before = article.name.slice(0, idx);
                const match = article.name.slice(idx, idx + q.length);
                const after = article.name.slice(idx + q.length);
                label.innerHTML = `${before}<mark>${match}</mark>${after}`;
            } else {
                label.textContent = article.name;
            }

            label.addEventListener("click", () => {
                this.renderArticle(article);
            });

            if (!article.active) {
                nodeRow.classList.add("text-muted");
                label.innerHTML = `<i>${article.name}</i>`;
            }

            nodeRow.appendChild(label);

            if (q && article.content) {
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = article.content;
                const contentText = tempDiv.textContent || "";

                const index = contentText.toLowerCase().indexOf(q);
                if (index !== -1) {
                    const snippet = contentText.substring(Math.max(index - 20, 0), index + q.length + 20);
                    const preview = document.createElement("div");
                    preview.classList.add("tree-snippet");

                    const before = snippet.slice(0, index);
                    const match = snippet.slice(index, index + q.length);
                    const after = snippet.slice(index + q.length);

                    preview.innerHTML = `... ${before}<mark>${match}</mark>${after} ...`;
                    nodeRow.appendChild(preview);
                }
            }

            li.appendChild(nodeRow);

            if (hasChildren && article.expanded) {
                this._renderTree(li, articles, article.id);
            }

            ul.appendChild(li);
        }

        container.appendChild(ul);
    }

    async renderArticle(article) {
        const display = this.root.el.querySelector(".o_article_display");

        if (!article) {
            if (display) {
                display.innerHTML = `
                    <div class='text-muted d-flex align-items-center px-3 py-2'>
                        <i class="fa fa-file-alt me-2"></i> No article selected or matching current filters.
                    </div>`;
            }
            return;
        }

        if (article && !article.active && !this.state.showArchived) {
            const display = this.root.el.querySelector(".o_article_display");
            if (display) display.innerHTML = `
                <div class='text-muted d-flex align-items-center px-3 py-2'>
                    <i class="fa fa-file-alt me-2"></i> This article is archived.
                </div>`;
            this.currentArticle = null;
            return;
        }

        this.currentArticle = article;
        this.state.currentArticleName = article.name;
        this.state.currentArticleId = article.id;
        this.state.isActive = article.active;
        this.state.currentArticle = article;
        this.state.viewsCount = article.views_count || 0;
        this.state.likesCount = article.likes_count || 0;
        this.state.likedByIds = article.liked_by_ids || [];
        localStorage.setItem("last_article_id", article.id);

        const currentHash = window.location.hash;
        const newHash = this._updateUrlParam(currentHash, 'article_id', article.id);
        history.replaceState(null, '', newHash);

        const trail = this.getBreadcrumbTrail(article.id) || [];
        this.state.breadcrumbTrail = trail;

        let parentId = article.parent_id;
        while (parentId) {
            const parent = this.articles.find(a => a.id === parentId);
            if (parent) {
                parent.expanded = true;
                parentId = parent.parent_id;
            } else break;
        }
        this._refreshTree(this.isFilteredView);
        setTimeout(() => {
            const selected = this.root.el.querySelector(".tree-node.selected-row");
            if (selected) selected.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 100);

        if (!this.articleContentCache.has(article.id)) {
            const [rec] = await this.orm.read("knowledge.article", [article.id], ["content"]);
            const html = rec.content || "";
            this.articleContentCache.set(article.id, { html, text: "" });
            toTextAsync(html, (txt) => {
                const cached = this.articleContentCache.get(article.id);
                if (cached) cached.text = txt;
            });
        }
        const cached = this.articleContentCache.get(article.id);
        display.innerHTML = cached.html || "<em>No content</em>";

        this.state.favoriteMap[article.id] = !!this.state.favoriteMap[article.id];

        const createdUserTuple = article.create_uid || [];
        const modifiedUserTuple = article.write_uid || [];
        const createdUserId = createdUserTuple[0];
        const modifiedUserId = modifiedUserTuple[0];

        this.state.createdBy = createdUserTuple[1] || "";
        this.state.createdByAvatar = createdUserId ? `/web/image/res.users/${createdUserId}/image_128` : "";
        this.state.createdOn = article.create_date;
        this.state.createdAgo = getTimeAgo(article.create_date);

        this.state.modifiedBy = modifiedUserTuple[1] || "";
        this.state.modifiedByAvatar = modifiedUserId ? `/web/image/res.users/${modifiedUserId}/image_128` : "";
        this.state.modifiedOn = article.write_date;
        this.state.modifiedAgo = getTimeAgo(article.write_date);

        this.render();

        if (!this.viewedArticles.has(article.id)) {
            this.viewedArticles.add(article.id);
            sessionStorage.setItem("viewedArticles", JSON.stringify([...this.viewedArticles]));
            setTimeout(async () => {
                try {
                    await jsonRpc("/knowledge/article/increment_view", { article_id: article.id });
                } catch (e) {
                    console.warn("Failed to update view count", e);
                }
            }, 1000);
        }

        this._loadChatter(article);
    }

    async editArticle() {
        if (!this.currentArticle) return;

        // Resolve content-only view ID via ir.model.data (XML ID lookup)
        let contentViewId = false;
        try {
            const result = await this.orm.call(
                'ir.model.data', 'check_object_reference',
                ['i8_knowledge_management', 'view_knowledge_article_content_only_form']
            );
            if (result && result[1]) contentViewId = result[1];
        } catch (_e) { /* fall back to default view */ }

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t("Edit: " + this.currentArticle.name),
            res_model: 'knowledge.article',
            res_id: this.currentArticle.id,
            target: 'new',
            views: [[contentViewId, 'form']],
            context: {
                from_split: true,
                default_name: this.currentArticle.name,
            },
        }, {
            onClose: async () => {
                const [updated] = await this.orm.read('knowledge.article', [this.currentArticle.id], [
                    'id', 'name', 'content', 'parent_id', 'write_date', 'write_uid'
                ]);
                updated.parent_id = updated.parent_id ? updated.parent_id[0] : null;

                this.currentArticle = { ...(this.currentArticle || {}), ...updated };

                const html = updated.content || "";
                this.articleContentCache.set(updated.id, { html, text: "" });
                toTextAsync(html, (txt) => {
                    const cached = this.articleContentCache.get(updated.id);
                    if (cached) cached.text = txt;
                });

                const item = this.allArticles.find(a => a.id === updated.id);
                if (item) {
                    item.name = updated.name;
                    item.write_date = updated.write_date;
                    item.write_uid = updated.write_uid;
                }

                this._refreshTree(this.isFilteredView);

                this.renderArticle(this.currentArticle);
            }
        });
    }

    _bindUI() {
        const sidebarSearchInput  = this.root.el.querySelector(".o_article_search_input");
        const matchCount = this.root.el.querySelector(".o_article_match_count");
        const clearIcon = this.root.el.querySelector(".o_clear_search");

        if (sidebarSearchInput ) {
            sidebarSearchInput .addEventListener("input", () => {
                const q = sidebarSearchInput.value.toLowerCase();
                this.searching = !!q;

                if (!q) {
                    this.filteredArticles = [];
                    matchCount.classList.add("d-none");
                    clearIcon.classList.add("d-none");
                    this._refreshTree(false);
                    return;
                }

                clearIcon.classList.remove("d-none");
                this.filteredArticles = this._getFilteredWithAncestors(q);
                matchCount.textContent = `${this.filteredArticles.length} match${this.filteredArticles.length !== 1 ? 'es' : ''} found`;
                matchCount.classList.remove("d-none");
                this._refreshTree(true);
            });

            clearIcon.addEventListener("click", () => {
                sidebarSearchInput .value = "";
                this.filteredArticles = [];
                this.searching = false;
                clearIcon.classList.add("d-none");
                matchCount.classList.add("d-none");
                this._refreshTree(false);
            });
        }
    }

    _getFilteredWithAncestors(query) {
        const q = (query || "").toLowerCase();
        const deep = !!this.state.searchInContent;

        const matches = this.articles.filter(a => {
            if ((a.name || "").toLowerCase().includes(q)) return true;
            if (!deep) return false;
            const cached = this.articleContentCache.get(a.id);
            return !!cached && !!cached.text && cached.text.includes(q);
        });

        const result = new Set(matches);
        for (const article of matches) {
            let parentId = article.parent_id;
            while (parentId) {
                const parent = this.articles.find(a => a.id === parentId);
                if (parent && !result.has(parent)) {
                    result.add(parent);
                    parentId = parent.parent_id;
                } else break;
            }
        }
        return Array.from(result);
    }

    async loadTags() {
        const tags = await this.orm.searchRead("knowledge.tag", [], ["id", "name"]);
        this.state.availableTags = tags;
        this.tagIdToName = new Map(tags.map(t => [t.id, t.name]));
    }

    _initSplitter() {
        const splitter = this.splitter.el;
        const sidebar = this.root.el.querySelector(".o_knowledge_sidebar");

        let isDragging = false;

        splitter.addEventListener("mousedown", (e) => {
            if (e.target.closest(".o_sidebar_patch")) return;
            if (this.state.sidebarCollapsed) return;

            isDragging = true;
            document.body.style.cursor = "col-resize";
            e.preventDefault();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            const offsetLeft = e.clientX;
            if (offsetLeft > 150 && offsetLeft < 600) {
                sidebar.style.width = offsetLeft + "px";
            }
        });

        document.addEventListener("mouseup", () => {
            if (isDragging) {
                isDragging = false;
                document.body.style.cursor = "";
                const w = Math.round(sidebar.getBoundingClientRect().width);
                if (w >= 150 && w <= 600) {
                    localStorage.setItem("sidebar_width", String(w));
                }
            }
        });
    }

    _newArticleAutoFocus() {
        document.addEventListener("transitionend", (e) => {
            if (this.state.showNewArticlePanel && e.target.classList.contains("new-article-panel")) {
                const input = this.root.el.querySelector("#new_article_input");
                if (input) input.focus();
            }
        });
    }

    _saveOnEnter() {
        setTimeout(() => {
            const input = this.root.el.querySelector("#new_article_input");
            if (input) input.focus();
        }, 0);

        this.root.el.querySelector("#new_article_input")?.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                this.createQuickArticle();
            }
        });
    }

    _onGlobalClick(e) {
        const bcNode = e.target.closest("[data-id]");
        if (bcNode) {
            const id = parseInt(bcNode.dataset.id);
            const article = this.articles.find(a => a.id === id);
            if (article) return this.renderArticle(article);
        }

        const card = this.cardPanel?.el;
        const toggle = this.cardToggleIcon?.el;

        if (!card || !this.state.showCardPanel) return;

        const clickedInsideCard = card.contains(e.target);
        const clickedToggle = toggle && toggle.contains(e.target);

        if (!clickedInsideCard && !clickedToggle) {
            this._closeCardPanel();
        }
    }

    _onEscapeKey(e) {
        if (e.key !== "Escape") return;

        const el = document.activeElement;
        if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) {
            el.blur();
        }

        const closedSomething = this._closeAllOverlays();
        if (closedSomething) {
            e.preventDefault();
            e.stopPropagation();
        }
    }

    _closeAllOverlays() {
        let closed = false;
        const close = (cond, action) => {
            if (!cond) return;
            closed = true;
            if (typeof action === "function") action();
            else this.state[action] = false;
        };

        close(this.state.showCardPanel, () => this._closeCardPanel());

        close(this.state.showSearchPanel, () =>
            this.closeSearchPanel ? this.closeSearchPanel() : (this.clearSearch?.(), this.state.showSearchPanel = false)
        );

        close(this.state.showFilterOverlay, "showFilterOverlay");

        close(this.state.showVersionHistoryPanel, "showVersionHistoryPanel");
        close(this.state.showDiffPanel, () => this.closeDiffPanel && this.closeDiffPanel());

        close(this.state.showNewArticlePanel, "showNewArticlePanel");

        close(this.state.showRenameModal, "showRenameModal");
        close(this.state.showMoveModal, "showMoveModal");
        close(this.state.showArchiveModal, "showArchiveModal");
        close(this.state.showUnarchiveModal, "showUnarchiveModal");
        close(this.state.showCopyModal, "showCopyModal");
        close(this.state.showTagModal, "showTagModal");
        close(this.state.showDropdown, "showDropdown");
        close(this.state.showMoreOptions, "showMoreOptions");

        if (closed) this.render();
        return closed;
    }

    async _loadChatter(article) {
        this.currentArticle = article;
        this._renderComments();
    }

    async _renderComments() {
        const container = this.root.el.querySelector(".comment-list");
        if (!container || !this.currentArticle) return;

        const messages = await jsonRpc(`/knowledge/article/${this.currentArticle.id}/messages`, {});
        const threadMap = new Map();

        for (const msg of messages) {
            msg.children = [];
            threadMap.set(msg.id, msg);
        }

        for (const msg of messages) {
            if (msg.parent_id && threadMap.has(msg.parent_id)) {
                threadMap.get(msg.parent_id).children.push(msg);
            }
        }

        const topLevel = messages.filter(msg => !msg.parent_id);

        container.innerHTML = "";
        for (const msg of topLevel) {
            container.appendChild(this._renderMessageThread(msg));
        }

        const topBox = document.createElement("div");
        topBox.className = "o_comment_box mt-3";
        topBox.innerHTML = `
            <textarea class="form-control comment-input mb-2" placeholder="Add a comment..."></textarea>
            <button class="btn btn-primary">
                <span class="spinner-border spinner-border-sm d-none me-2" role="status" aria-hidden="true"></span>
                <span>Post</span>
            </button>
        `;
        topBox.querySelector(".btn-primary").addEventListener("click", () => {
            this.postComment(null, topBox);
        });
        container.appendChild(topBox);

    }

    _renderMessageThread(msg) {
        const wrapper = document.createElement("div");
        wrapper.className = "comment border rounded p-2 mb-2";
        const msgCreatedAgo = getTimeAgo(msg.date);

        wrapper.innerHTML = `
            <strong>${msg.author}</strong>
            <div class="text-muted small">${msgCreatedAgo}</div>
            <div>${msg.body}</div>
            <button class="btn btn-link p-0 mt-1 reply-btn">Reply</button>
            <div class="reply-section d-none mt-2">
                <textarea class="form-control reply-input mb-1" data-parent-id="${msg.id}"></textarea>
                <button class="btn btn-sm btn-primary">Post</button>
            </div>
        `;

        const replyBtn = wrapper.querySelector(".reply-btn");
        const replySection = wrapper.querySelector(".reply-section");
        const postBtn = replySection.querySelector(".btn-primary");

        replyBtn.addEventListener("click", () => replySection.classList.toggle("d-none"));
        postBtn.addEventListener("click", (e) => {
            const wrapper = e.target.closest(".reply-section");
            this.postComment(msg.id, wrapper);
        });
        postBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm d-none me-2" role="status" aria-hidden="true"></span>
            <span>Post</span>
        `;

        if (msg.children.length) {
            const childContainer = document.createElement("div");
            childContainer.className = "child-comments ps-4";

            for (const child of msg.children) {
                const childThread = this._renderMessageThread(child);
                childContainer.appendChild(childThread);
            }

            wrapper.appendChild(childContainer);
        }

        return wrapper;
    }

    async postComment(parent_id = null, section = null) {
        const root = this.root.el;
        const input = section?.querySelector("textarea.comment-input, textarea.reply-input");
        const postBtn = section?.querySelector(".btn-primary");
        const spinner = postBtn?.querySelector(".comment-list");

        if (!input) {
            console.warn("Comment textarea not found");
            return;
        }

        const content = input.value.trim();
        if (!content) {
            console.warn("Comment is empty");
            return;
        }

        if (spinner) spinner.classList.remove("d-none");
        if (postBtn) postBtn.disabled = true;
        this.state.commentLoading = true;

        const parsedParentId = parseInt(parent_id);
        const isReply = !isNaN(parsedParentId) && parsedParentId > 0;

        const kwargs = {
            body: content,
            message_type: "comment",
        };

        if (isReply) {
            kwargs.parent_id = parsedParentId;
        }

        try {
            const message_id = await this.orm.call(
                "knowledge.article",
                "message_post",
                [this.currentArticle.id],
                kwargs
            );

            input.value = "";
            await this._renderComments();
            this._showToast("Comment added successfully.");
        } catch (e) {
            console.error("Error posting comment", e);
        } finally {
            if (spinner) spinner.classList.add("d-none");
            if (postBtn) postBtn.disabled = false;
            this.state.commentLoading = false;
        }
    }

    async toggleFavorite() {
        const articleId = this.state.currentArticleId;
        if (!articleId) return;
        try {
            const res = await this.orm.call("knowledge.article", "action_toggle_follow", [articleId]);
            this.state.favoriteMap[articleId] = !!res.following;
            this.render();
        } catch (e) {
            console.error("toggleFavorite failed", e);
            this._showToast("Could not update favorite.", "error");
        }
    }

    async toggleFavoritesFilter() {
        this.state.onlyFavorites = !this.state.onlyFavorites;
        localStorage.setItem("only_favorites", this.state.onlyFavorites ? "1" : "0");
        this.filterArticles();
    }

    async clearAllFilters() {
        this.state.selectedTags = [];
        this.state.onlyFavorites = false;
        this.state.showArchived = false;

        localStorage.removeItem("selected_tags");
        localStorage.removeItem("only_favorites");

        await this.loadArticles();
        this.filterArticles();
        this.render();
        this._showToast("All filters cleared.", "info");
    }

    onSearchInput(ev) {
        this.state.query = ev.target.value;
        this.debouncedSearch();
    }

    async _performSearch() {
        const raw = this.state.query || "";
        const query = raw.trim().toLowerCase();

        if (!query) {
            this.state.searchResults = [];
            return;
        }

        const source = this.articles || [];

        if (!this.state.searchInContent) {
            this.state.searchResults = source
                .filter(a => (a.name || "").toLowerCase().includes(query))
                .map(a => ({ ...a, snippet: "" }));
            return;
        }

        const MAX_BATCH = 200;
        const missingIds = [];
        for (const a of source) {
            if (!this.articleContentCache.has(a.id)) {
                missingIds.push(a.id);
                if (missingIds.length >= MAX_BATCH) break;
            }
        }

        if (missingIds.length) {
            try {
                const recs = await this.orm.read("knowledge.article", missingIds, ["content"]);
                for (let i = 0; i < recs.length; i++) {
                    const html = recs[i]?.content || "";
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, "text/html");
                    const text = (doc.body?.textContent || "").toLowerCase();
                    this.articleContentCache.set(missingIds[i], { html, text });
                }
            } catch (e) {
                console.warn("Content batch read failed:", e);
            }
        }

        const results = [];
        for (const a of source) {
            const name = (a.name || "").toLowerCase();
            const nameMatch = name.includes(query);

            const cached = this.articleContentCache.get(a.id);
            const text = cached?.text || "";
            const contentMatch = text ? text.includes(query) : false;

            if (nameMatch || contentMatch) {
                let snippet = "";
                if (text) {
                    const idx = text.indexOf(query);
                    if (idx !== -1) {
                        const start = Math.max(0, idx - 40);
                        const end = idx + query.length + 40;
                        snippet = "... " + text.slice(start, end).trim() + " ...";
                    }
                }
                results.push({ ...a, snippet });
            }
        }

        this.state.searchResults = results;
    }

    clearSearch() {
        this.state.query = "";
        this.state.searchResults = [];

        const inputEl = this.root.el.querySelector(".o_slide_search_input");
        if (inputEl) {
            inputEl.value = "";
        }

        this.render();
    }

    openSearchPanel() {
        this.state.showSearchPanel = true;
        this.clearSearch();
        setTimeout(() => {
            this.root.el.querySelector(".o_slide_search_input")?.focus();
        }, 0);
    }

    closeSearchPanel() {
        this.clearSearch();
        this.state.showSearchPanel = false;
    }

    toggleMetadata() {
        this.state.showMetadata = !this.state.showMetadata;
    }

    toggleMoreOptions() {
        this.state.showMoreOptions = !this.state.showMoreOptions;
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString();
    }

    onTagFilterChange(ev) {
        const selectedOptions = [...ev.target.options]
            .filter(opt => opt.selected)
            .map(opt => opt.value);
        this.state.selectedTags = selectedOptions.map(id => parseInt(id));
        localStorage.setItem("selected_tags", JSON.stringify(this.state.selectedTags));
        localStorage.setItem("only_favorites", this.state.onlyFavorites ? "1" : "0");
        this.filterArticles();
    }

    filterArticles() {
        const base = [...this.allArticles];

        let result = [];
        if (this.state.showArchived) {
            const archived = base.filter(r => !r.active);
            const idsToInclude = new Set(archived.map(r => r.id));
            const idMap = new Map(base.map(r => [r.id, r]));

            for (const article of archived) {
                let parentId = article.parent_id;
                while (parentId) {
                    const parent = idMap.get(parentId);
                    if (parent && !idsToInclude.has(parent.id)) {
                        idsToInclude.add(parent.id);
                        parentId = parent.parent_id;
                    } else break;
                }
            }
            result = base.filter(r => idsToInclude.has(r.id));
        } else {
            result = base.filter(r => r.active);
        }

        const selectedTags = this.state.selectedTags;
        const onlyFav = this.state.onlyFavorites;

        const matches = result.filter(article => {
            const tagMatch = !selectedTags.length || article.tag_ids_raw?.some(tagId => selectedTags.includes(tagId));
            const favMatch = !onlyFav || this.state.favoriteMap[article.id];
            return tagMatch && favMatch;
        });

        for (const a of base) delete a.isTagMatch;
        for (const article of matches) {
            if (selectedTags.length && article.tag_ids_raw?.some(tagId => selectedTags.includes(tagId))) {
                article.isTagMatch = true;
            }
        }

        const finalSet = new Set(matches);
        const fullMap = new Map(base.map(r => [r.id, r]));
        for (const article of matches) {
            let parentId = article.parent_id;
            while (parentId) {
                const parent = fullMap.get(parentId);
                if (parent && !finalSet.has(parent)) {
                    finalSet.add(parent);
                    parentId = parent.parent_id;
                } else break;
            }
        }
        const final = Array.from(finalSet);

        for (const article of final) {
            let parentId = article.parent_id;
            while (parentId) {
                const parent = fullMap.get(parentId);
                if (parent) {
                    parent.expanded = true;
                    parentId = parent.parent_id;
                } else break;
            }
        }

        this.articles = final;
        this.filteredArticles = final;

        this.sortFilteredArticles();

        const curId = this.state.currentArticleId;
        const stillVisible = final.find(a => a.id === curId);

        if (final.length === 0) {
            this.currentArticle = null;
            this.state.currentArticleId = null;
            this.renderArticle(null);
        } else if (!stillVisible) {
            const next = final[0];
            this.renderArticle(next);
        } else {
            this.renderArticle(stillVisible);
        }

        this._refreshTree(true);

        localStorage.setItem("selected_tags", JSON.stringify(this.state.selectedTags));
        localStorage.setItem("only_favorites", this.state.onlyFavorites ? "1" : "0");
        localStorage.setItem("show_archived", this.state.showArchived ? "1" : "0");
    }

    exportArticle() {
        if (!this.currentArticle) return;

        const contentDiv = document.createElement("div");
        contentDiv.innerHTML = `
            <div style="font-family: 'Segoe UI', sans-serif; padding: 20px;">
                <h1>${this.currentArticle.name}</h1>
                <p style="font-size: 12px; color: #666;">
                    Created by ${this.state.createdBy} · ${new Date(this.state.createdOn).toLocaleString()}<br>
                    Last edited by ${this.state.modifiedBy} · ${new Date(this.state.modifiedOn).toLocaleString()}
                </p>
                <hr style="margin: 12px 0;">
                ${this.currentArticle.content}
            </div>
        `;

        const opt = {
            margin:       0.5,
            filename:     `${this.currentArticle.name.replace(/[^a-z0-9]/gi, '_')}.pdf`,
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { scale: 2 },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        const lib = window.html2pdf;
        if (lib) {
            lib().set(opt).from(contentDiv).save();
            this._showToast("Article exported successfully.");
        } else {
            const win = window.open('', '_blank');
            win.document.write('<html><head><title>' + this.currentArticle.name + '</title></head><body>' + contentDiv.innerHTML + '</body></html>');
            win.document.close(); win.focus(); win.print();
            this._showToast("html2pdf unavailable — opened print dialog instead.");
        }
    }

    shareArticle() {
        if (!this.state.currentArticleId || !this.currentArticle?.share_token) return;

        const url = `${window.location.origin}/knowledge/article/${this.currentArticle.share_token}`;

        navigator.clipboard.writeText(url).then(() => {
            this.state.showCopied = true;
            setTimeout(() => {
                this.state.showCopied = false;
                this.render();
            }, 2000);
            this.render();
            this._showToast("Article link copied successfully.");
        }).catch(err => {
            console.error("Clipboard copy failed:", err);
            alert("Failed to copy link.");
        });
    }

    async openVersionHistory() {
        this.state.showVersionHistoryPanel = true;
        const versions = await this.orm.searchRead("knowledge.article.version", [
            ["article_id", "=", this.state.currentArticleId]
        ], ["id", "version_number", "create_date", "user_id"], { order: "version_number desc" });

        this.state.versionHistory = versions;
    }

    get markup() {
        return markup;
    }

    get currentUid() {
        return session.uid || (odoo.session_info && odoo.session_info.uid) || 0;
    }

    async openDiffPanel(oldId, currentId) {
        const [wizard] = await this.orm.create('knowledge.version.compare.wizard', [{
            article_id: this.state.currentArticleId,
            old_version_id: oldId,
            current_version_id: currentId,
        }]);

        const [record] = await this.orm.read('knowledge.version.compare.wizard', [wizard], ['diff_html']);
        this.state.diffHtml = record.diff_html;
        this.state.oldVersionId = oldId;
        this.state.currentVersionId = currentId;
        this.state.showDiffPanel = true;
    }

    closeDiffPanel() {
        this.state.showDiffPanel = false;
        this.state.diffHtml = '';
        this.state.oldVersionId = null;
        this.state.currentVersionId = null;
    }

    async createCopy() {
        if (!this.currentArticle) return;

        const [original] = await this.orm.read("knowledge.article", [this.currentArticle.id], ["name"]);
        this.state.copyTitle = original.name + " (copy)";
        this.state.showCopyModal = true;
    }

    cancelCopy() {
        this.state.showCopyModal = false;
        this.state.copyTitle = '';
    }

    async confirmCopy() {
        const newName = this.state.copyTitle.trim();
        if (!newName) {
            alert("Name cannot be empty.");
            return;
        }

        try {
            const [original] = await this.orm.read("knowledge.article", [this.currentArticle.id], [
                "content", "tag_ids", "parent_id", "is_published"
            ]);

            const [newId] = await this.orm.create("knowledge.article", [{
                name: newName,
                content: original.content,
                tag_ids: original.tag_ids.map(id => [4, id]),
                parent_id: original.parent_id?.[0] || false,
                is_published: original.is_published,
                active: true,
            }]);

            await this.loadArticles();
            const newArticle = this.articles.find(a => a.id === newId);
            if (newArticle) this.renderArticle(newArticle);

            this._showToast("Article copied successfully.");
        } catch (err) {
            console.error("Failed to copy article:", err);
            alert("Failed to copy article.");
        } finally {
            this.state.showCopyModal = false;
            this.state.copyTitle = '';
        }
    }

    _showToast(message = "", type = "success") {
        const toast = document.createElement("div");
        toast.className = "toast-message";
        toast.innerText = message;

        const colors = {
            info: "#333",       // default
            success: "#28a745", // green
            warning: "#ffc107", // orange
            error: "#dc3545",   // red
        };

        const bg = colors[type] || colors.info;

        Object.assign(toast.style, {
            position: "fixed",
            bottom: "20px",
            right: "20px",
            background: bg,
            color: "#fff",
            padding: "10px 20px",
            borderRadius: "5px",
            zIndex: 9999,
            opacity: 0,
            transition: "opacity 0.3s ease-in-out",
        });

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = 1;
        }, 100);

        setTimeout(() => {
            toast.style.opacity = 0;
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 2500);
    }

    renameArticle() {
        this.state.renameTitle = this.state.currentArticleName;
        this.state.showRenameModal = true;
    }

    cancelRename() {
        this.state.showRenameModal = false;
        this.state.renameTitle = '';
    }

    async confirmRename() {
        const newTitle = this.state.renameTitle.trim();
        if (!newTitle || newTitle === this.state.currentArticleName) {
            this.state.showRenameModal = false; return;
        }
        await this.orm.write("knowledge.article", [this.state.currentArticleId], { name: newTitle });
        const item = this.allArticles.find(a => a.id === this.state.currentArticleId);
        if (item) item.name = newTitle;
        const cur = this.currentArticle;
        if (cur?.id === item?.id) { cur.name = newTitle; this.state.currentArticleName = newTitle; }
        this._refreshTree(this.isFilteredView);
        this.state.showRenameModal = false;
        this._showToast("Article renamed successfully.");
    }

    moveToFolder() {
        this.state.moveTargetId = this.currentArticle.parent_id || null;
        this.state.selectedMoveTarget = this.currentArticle.parent_id || null;
        this.state.showMoveModal = true;
    }

    cancelMove() {
        this.state.showMoveModal = false;
        this.state.moveTargetId = null;
        this.state.selectedMoveTarget = null;
    }

    selectMoveTarget(articleId) {
        const currentId = this.state.currentArticleId;

        // Prevent selecting self
        if (articleId === currentId) {
            this._showToast("An article cannot be its own parent.", "warning");
            return;
        }

        // Prevent selecting any descendant (would create a cycle)
        const isDescendant = (candidateId) => {
            let node = this.articles.find(a => a.id === candidateId);
            while (node) {
                if (node.parent_id === currentId) return true;
                node = this.articles.find(a => a.id === node.parent_id);
            }
            return false;
        };

        if (articleId && isDescendant(articleId)) {
            this._showToast("Cannot move an article into one of its own children.", "warning");
            return;
        }

        this.state.moveTargetId = articleId;
        this.state.selectedMoveTarget = articleId;
    }

    async confirmMove() {
        const currentId = this.state.currentArticleId;
        const targetId = this.state.moveTargetId;

        // Final guard before write
        if (targetId === currentId) {
            this._showToast("An article cannot be its own parent.", "warning");
            return;
        }

        await this.orm.write("knowledge.article", [currentId], { parent_id: targetId });
        const item = this.allArticles.find(a => a.id === currentId);
        if (item) item.parent_id = targetId || null;
        this.filterArticles();
        this.renderArticle(item);
        this.state.showMoveModal = false;
        this._showToast("Article moved successfully.");
    }

    getBreadcrumbTrail(articleId) {
        const trail = [];
        let current = this.articles.find(a => a.id === articleId);
        while (current) {
            trail.unshift(current);
            current = this.articles.find(a => a.id === current.parent_id);
        }
        return trail;
    }

    handleBreadcrumbClick(ev) {
        const target = ev.target.closest('[data-id]');
        if (!target) return;

        const id = parseInt(target.dataset.id);
        if (!isNaN(id)) {
            const article = this.articles.find(a => a.id === id);
            if (article) this.renderArticle(article);
        }
    }

    _onTreeToggleClick(ev) {
        const icon = ev.target.closest(".tree-toggle-icon");
        if (!icon) return;

        const li = icon.closest("li.tree-item");
        if (!li) return;

        const articleId = parseInt(li.dataset.articleId);
        const article = this.articles.find(a => a.id === articleId);
        if (!article) return;

        article.expanded = !article.expanded;
        localStorage.setItem("expanded_nodes", JSON.stringify(
            this.articles.filter(a => a.expanded).map(a => a.id)
        ));
        this._refreshTree(this.isFilteredView);
    }

    openTagModal() {
        if (!this.currentArticle) return;
        this.state.showTagModal = true;
        this.state.tagSearch = '';
        this.state.selectedTagIds = [...(this.currentArticle?.tag_ids_raw || [])];
    }

    cancelTagModal() {
        this.state.showTagModal = false;
        this.state.selectedTagIds = [];
    }

    toggleTagSelection(tagId) {
        const id = parseInt(tagId);
        const list = this.state.selectedTagIds;
        if (list.includes(id)) {
            this.state.selectedTagIds = list.filter(x => x !== id);
        } else {
            this.state.selectedTagIds = [...list, id];
        }
    }

    filteredAvailableTags() {
        const query = this.state.tagSearch.toLowerCase();
        return this.state.availableTags.filter(tag => tag.name.toLowerCase().includes(query));
    }

    async confirmTagsUpdate() {
        const ids = this.state.selectedTagIds.map(Number);
        await this.orm.write("knowledge.article", [this.currentArticle.id], { tag_ids: [6, 0, ids] });

        const item = this.allArticles.find(a => a.id === this.currentArticle.id);
        if (item) {
            item.tag_ids_raw = ids;
            item.tag_ids = ids.map(id => this.tagIdToName.get(id) || "");
        }
        this.filterArticles();
        this.renderArticle(item);
        this.state.showTagModal = false;
        this._showToast("Tag updated successfully.");
    }

    async archiveArticle() {
        const articleId = this.state.currentArticleId;
        const article = this.articles.find(a => a.id === articleId);
        if (!article) return;

        this.state.canArchive = false;

        try {
            const [rec] = await this.orm.read("knowledge.article", [articleId], ["create_uid"]);
            const ownerId = Array.isArray(rec.create_uid) ? Number(rec.create_uid[0]) : NaN;
            const uid = Number(session.uid || (odoo.session_info && odoo.session_info.uid) || 0);
            const isOwner = ownerId === uid;
            const isAdmin = !!(session.is_system);

            if (isOwner || isAdmin) {
                this.state.canArchive = true;
                this.state.showArchiveModal = true;
                this.render();
            } else {
                this._showToast("Only the article owner or Admin can archive this article.", "warning");
            }
        } catch (e) {
            console.error("archiveArticle check failed", e);
        }
    }

    cancelArchive() {
        this.state.showArchiveModal = false;
    }

    async confirmArchive() {
        try {
            const archivedId = this.state.currentArticleId;
            await this.orm.write("knowledge.article", [archivedId], { active: false });
            this.state.showArchiveModal = false;

            const item = this.allArticles.find(a => a.id === archivedId);
            if (item) item.active = false;

            this.articleContentCache.delete(archivedId);

            this.filterArticles();

            if (!this.state.showArchived) {
                const next = this.articles.length ? this.articles[0] : null;
                this.renderArticle(next);
            } else {
                const stillThere = this.articles.find(a => a.id === archivedId) || null;
                this.renderArticle(stillThere);
            }

            this._showToast("Article archived successfully.");
        } catch (err) {
            console.error("Archiving failed", err);
        }
    }

    async unarchiveArticle() {
        const articleId = this.state.currentArticleId;
        const article = this.articles.find(a => a.id === articleId);
        if (!article) return;

        this.state.canUnarchive = false;

        try {
            const [rec] = await this.orm.read("knowledge.article", [articleId], ["create_uid"]);
            const ownerId = Array.isArray(rec.create_uid) ? Number(rec.create_uid[0]) : NaN;
            const uid = Number(session.uid || (odoo.session_info && odoo.session_info.uid) || 0);
            const isOwner = ownerId === uid;
            const isAdmin = !!(session.is_system);

            if (isOwner || isAdmin) {
                this.state.canUnarchive = true;
                this.state.showUnarchiveModal = true;
                this.render();
            } else {
                this._showToast("Only the article owner or Admin can unarchive this article.", "warning");
            }
        } catch (e) {
            console.error("unarchiveArticle check failed", e);
        }
    }

    cancelUnarchive() {
        this.state.showUnarchiveModal = false;
    }

    async confirmUnarchive() {
        try {
            const id = this.state.currentArticleId;
            await this.orm.write("knowledge.article", [id], { active: true });
            this.state.showUnarchiveModal = false;

            const item = this.allArticles.find(a => a.id === id);
            if (item) item.active = true;

            this.filterArticles();

            const cur = this.articles.find(a => a.id === id) || this.articles[0] || null;
            this.renderArticle(cur);

            this._showToast("Article unarchived successfully.");
        } catch (err) {
            console.error("Unarchiving failed", err);
        }
    }

    async toggleArchivedVisibility() {
        this.state.showArchived = !this.state.showArchived;
        localStorage.setItem("show_archived", this.state.showArchived ? "1" : "0");
        this.filterArticles();
    }

    get isFilteredView() {
        return this.searching || this.state.selectedTags.length > 0 || this.state.onlyFavorites;
    }

    createArticle() {
        this.openNewArticlePanel();
    }

    toggleTag(tag) {
        const tagId = tag.id;
        if (this.state.selectedTags.includes(tagId)) {
            this.state.selectedTags = this.state.selectedTags.filter(tid => tid !== tagId);
        } else {
            this.state.selectedTags.push(tagId);
        }
        this.filterArticles();
    }

    isTagSelected(tagId) {
        return this.state.selectedTags.includes(tagId);
    }

    toggleCollapse(id) {
        if (this.state.collapsedNodes.has(id)) {
            this.state.collapsedNodes.delete(id);
        } else {
            this.state.collapsedNodes.add(id);
        }
        this.render();
    }

    openNewArticlePanel() {
        this.state.showNewArticlePanel = true;
        this.state.newArticleTitle = "";
        this.state.creatingArticle = false;
    }

    cancelNewArticle() {
        this.state.showNewArticlePanel = false;
        this.state.newArticleTitle = "";
    }

    async createQuickArticle() {
        if (this.state.creatingArticle) return;
        const title = this.state.newArticleTitle.trim();
        if (!title) return;

        this.state.creatingArticle = true;
        try {
            const [newId] = await this.orm.create("knowledge.article", [{
                name: title, parent_id: this.currentArticle?.id || false, is_published: true, active: true,
            }]);
            const [rec] = await this.orm.read("knowledge.article", [newId],
                ["id","name","parent_id","tag_ids","active","display_name","views_count","likes_count","liked_by_ids","create_date","write_date","create_uid","write_uid","share_token"]);
            const newItem = {
                ...rec,
                parent_id: rec.parent_id ? rec.parent_id[0] : null,
                tag_ids_raw: rec.tag_ids,
                tag_ids: (rec.tag_ids || []).map(id => this.tagIdToName.get(id) || ""),
                expanded: true,
            };
            this.allArticles.push(newItem);
            this.filterArticles();
            this.renderArticle(newItem);
            this._showToast(`Article: ${title} created successfully.`);
            setTimeout(() => this._showToast("Please use edit to add content.", "info"), 3000);
        } finally {
            this.state.creatingArticle = false;
            this.state.showNewArticlePanel = false;
            this.state.newArticleTitle = "";
        }
    }

    async toggleLike() {
        const articleId = this.state.currentArticleId;
        if (!articleId) return;
        try {
            const res = await this.orm.call("knowledge.article", "action_toggle_like", [articleId]);
            this.state.likedByIds = res.liked_by_ids || [];
            this.state.likesCount = res.likes_count || 0;
            if (this.currentArticle?.id === articleId) {
                this.currentArticle.liked_by_ids = this.state.likedByIds;
                this.currentArticle.likes_count = this.state.likesCount;
            }
            this.render();
        } catch (e) {
            console.error("toggleLike failed", e);
            this._showToast("Could not update like.", "error");
        }
    }

    expandAll() {
        this.articles.forEach(a => a.expanded = true);
        localStorage.setItem("expanded_nodes", JSON.stringify(
            this.articles.filter(a => a.expanded).map(a => a.id)
        ));
        this._refreshTree(this.isFilteredView);
    }

    collapseAll() {
        this.articles.forEach(a => a.expanded = false);
        localStorage.setItem("expanded_nodes", JSON.stringify(
            this.articles.filter(a => a.expanded).map(a => a.id)
        ));
        this._refreshTree(this.isFilteredView);
    }

    onSortChange(ev) {
        this.state.sortOrder = ev.target.value;
        localStorage.setItem("article_sort_order", this.state.sortOrder);
        this.sortArticles();
        this._refreshTree(this.isFilteredView);
    }

    sortArticles() {
        const key = this.state.sortOrder;
        const getTime = s => new Date(s).getTime();

        const comparator = {
            name: (a, b) => a.name.localeCompare(b.name),
            name_desc: (a, b) => b.name.localeCompare(a.name),
            created: (a, b) => getTime(a.create_date) - getTime(b.create_date),
            created_desc: (a, b) => getTime(b.create_date) - getTime(a.create_date),
            updated_desc: (a, b) => getTime(b.write_date) - getTime(a.write_date),
            likes_desc: (a, b) => (b.likes_count || 0) - (a.likes_count || 0),
            views_desc: (a, b) => (b.views_count || 0) - (a.views_count || 0),
        }[key];

        if (comparator) {
            this.articles.sort(comparator);
        }
    }

    sortFilteredArticles() {
        const key = this.state.sortOrder;
        const getTime = s => new Date(s).getTime();

        const comparator = {
            name: (a, b) => a.name.localeCompare(b.name),
            name_desc: (a, b) => b.name.localeCompare(a.name),
            created: (a, b) => getTime(a.create_date) - getTime(b.create_date),
            created_desc: (a, b) => getTime(b.create_date) - getTime(a.create_date),
            updated_desc: (a, b) => getTime(b.write_date) - getTime(a.write_date),
            likes_desc: (a, b) => (b.likes_count || 0) - (a.likes_count || 0),
            views_desc: (a, b) => (b.views_count || 0) - (a.views_count || 0),
        }[key];

        if (comparator) {
            this.filteredArticles.sort(comparator);
        }
    }

    _restorePersistedState() {
        const rawTags = JSON.parse(localStorage.getItem("selected_tags") || "[]");
        this.state.selectedTags = rawTags.map(id => parseInt(id));
        this.state.onlyFavorites = localStorage.getItem("only_favorites") === "1";
        this.state.showArchived = localStorage.getItem("show_archived") === "1";
        this.state.sortOrder = localStorage.getItem("article_sort_order") || "name";
        this.lastSelectedArticleId = parseInt(localStorage.getItem("last_article_id")) || null;
        const expandedIds = JSON.parse(localStorage.getItem("expanded_nodes") || "[]");
        this.expandedSet = new Set(expandedIds);

        this.state.sidebarCollapsed = localStorage.getItem("sidebar_collapsed") === "1";
    }

    _updateUrlParam(hash, key, value) {
        const [basePath, paramStr] = hash.replace(/^#/, '').split('?');
        const params = new URLSearchParams(paramStr || '');
        params.set(key, value);
        return `#${basePath}?${params.toString()}`;
    }

    async _getPartnerId() {
        const uid = session.uid || (odoo.session_info && odoo.session_info.uid);
        if (!uid) return null;
        const [user] = await this.orm.read("res.users", [uid], ["partner_id"]);
        return user?.partner_id?.[0] ?? null;
    }

    toggleSearchInContent() {
        this.state.searchInContent = !this.state.searchInContent;
        localStorage.setItem("search_in_content", this.state.searchInContent ? "1" : "0");
        this._performSearch();
    }

    toggleSidebar() {
        this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
        localStorage.setItem("sidebar_collapsed", this.state.sidebarCollapsed ? "1" : "0");

        const rootEl = this.root.el;
        const sidebar = rootEl.querySelector(".o_knowledge_sidebar");

        if (this.state.sidebarCollapsed) {
            rootEl.classList.add("sidebar-collapsed");
        } else {
            rootEl.classList.remove("sidebar-collapsed");
            const savedWidth = parseInt(localStorage.getItem("sidebar_width"), 10);
            sidebar.style.width = (!isNaN(savedWidth) ? savedWidth : 280) + "px";
        }
    }

    _initStickyToolbar() {
        const scroller = this.root.el.querySelector(".o_knowledge_content");
        const header = this.root.el.querySelector(".o_article_toolbar");
        if (!scroller || !header) return;

        const onScroll = () => header.classList.toggle("is-stuck", scroller.scrollTop > 0);
        scroller.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
    }

    toggleCardPanel() {
        if (this.state.showCardPanel) {
            this._closeCardPanel();
        } else {
            this._openCardPanel();
        }
    }

    _openCardPanel() {
        this.state.showCardPanel = true;
        setTimeout(() => this._positionCardPanel(), 0);

        this._boundReposition = this._boundReposition || this._positionCardPanel.bind(this);
        window.addEventListener("scroll", this._boundReposition, true);
        window.addEventListener("resize", this._boundReposition);
    }

    _closeCardPanel() {
        this.state.showCardPanel = false;
        if (this._boundReposition) {
            window.removeEventListener("scroll", this._boundReposition, true);
            window.removeEventListener("resize", this._boundReposition);
        }
    }

    _positionCardPanel() {
        const toggle = this.cardToggleIcon?.el;
        const panel  = this.cardPanel?.el;
        if (!toggle || !panel) return;

        const t = toggle.getBoundingClientRect();
        const prevVis = panel.style.visibility;
        const prevDisp = panel.style.display;
        panel.style.visibility = "hidden";
        panel.style.display = "block";
        const pw = panel.offsetWidth || 256;
        panel.style.visibility = prevVis || "";
        panel.style.display = prevDisp || "";

        const gap = 8;
        let top = t.bottom + gap;
        let left = t.right - pw;

        const vw = window.innerWidth, vh = window.innerHeight;
        left = Math.max(8, Math.min(left, vw - pw - 8));
        const ph = panel.offsetHeight || 300;
        if (top + ph > vh - 8) top = Math.max(8, vh - ph - 8);

        Object.assign(panel.style, {
            position: "fixed",
            top: `${top}px`,
            left: `${left}px`,
            right: "auto",
            bottom: "auto",
        });
    }

}

function getTimeAgo(dateStr) {
    const now = new Date();
    const date = new Date(dateStr + 'Z');
    const seconds = Math.floor((now - date) / 1000);

    const intervals = [
        { label: 'year', seconds: 31536000 },
        { label: 'month', seconds: 2592000 },
        { label: 'day', seconds: 86400 },
        { label: 'hour', seconds: 3600 },
        { label: 'minute', seconds: 60 },
        { label: 'second', seconds: 1 },
    ];

    for (const interval of intervals) {
        const count = Math.floor(seconds / interval.seconds);
        if (count >= 1) {
            return `${count} ${interval.label}${count !== 1 ? 's' : ''} ago`;
        }
    }
    return 'just now';
}

function toTextAsync(html, cb) {
    const run = () => {
        const doc = new DOMParser().parseFromString(html || "", "text/html");
        cb((doc.body?.textContent || "").toLowerCase());
    };

    const ric = window.requestIdleCallback;
    if (typeof ric === "function") {
        ric(run, { timeout: 300 });
    } else {
        setTimeout(run, 0);
    }
}

registry.category("actions").add("knowledge_split_client", KnowledgeSplit);