class Header extends HTMLElement {
	connectedCallback() {
		this.innerHTML = `
			<header>
				<p class="header-title"><a href="./" tabindex="-1">${typeof commonset_header_title !== 'undefined' ? commonset_header_title : 'not-set'}</a></p>
			</header>
		`;
	}
}

class Footer extends HTMLElement {
	connectedCallback() {
		this.innerHTML = `
			<footer>
				<p>© 2026 ricevalley</p>
			</footer>`;
	}
}

const config_json = '/config.json';

async function fetch_config() {
	try {
		const res = await fetch(config_json);
		if (!res.ok) {
			throw new Error(`error status: ${res.status}`);
		}

		return await res.json();
	} catch (e) {
		console.error(e);
	}
}

window.addEventListener('DOMContentLoaded', () => {
	customElements.define('set-header', Header);
	customElements.define('set-footer', Footer);

	//head
	const common_head = `
		<title>${typeof commonset_page_title !== 'undefined' ? commonset_page_title : 'not-set | Not-set'}</title>
		<link rel="icon" sizes="any" href="/favicon.ico">
		<link rel="stylesheet" type="text/css" href="/common/fontawesome.all.min.css">
	`;
	document.head.insertAdjacentHTML('beforeend', common_head);
});