import Sortable from '/module/sortable.esm.js';

const inputBtn = document.getElementById('inputfilesSelecter');
const outputBtn = document.getElementById('outputfilesSelecter');
const execBtn = document.getElementById('execBtn');
const termBtn = document.getElementById('termBtn');
const processTextArea = document.getElementById('process');
const selectedOutputTextArea = document.getElementById('selectedOutputfiles');
const selecetdInputList = document.getElementById('selectedInputfiles');
const selecetdInputCounter = document.getElementById('selectedInputfilescount');
const execGuide = document.getElementById('formguid_process');
const fontSelectBtn = document.getElementById('captionFont');
const progressArea = document.getElementById('progressArea');
const progressBar = document.getElementById('progressBar');
const progressPercentage = document.getElementById('progressPercentage');
const presetSelector = document.getElementById('preset');
const HWEncodeSelector  = document.getElementById('HWEncode');
const inputFolderLink  = document.getElementById('inputFolderLink');
const outputFolderLink  = document.getElementById('outputFolderLink');

eel.expose(addLog);
eel.expose(addError);
eel.expose(showAlert);
eel.expose(quitProcess);
eel.expose(showProgress);
eel.expose(getAllLog);

let selectedCodec = null;
eel.selectEncoder('h264')().then(codec => {
	selectedCodec = codec;
});

let inputFilesPath = null;
let outputFilePath = null;
Sortable.create(selecetdInputList, {
	handle: '.handle',
	animation: 150,
	onEnd: function (e) {
		if (inputFilesPath !== null){
			const item = inputFilesPath.splice(e.oldIndex, 1)[0];
			inputFilesPath.splice(e.newIndex, 0, item);
		}
	}
});

let controllerInput;
inputBtn.addEventListener('click', async () => {
	const path = await eel.selectInputFiles()();
	if (path) {
		inputFilesPath = structuredClone(path);
		selecetdInputList.replaceChildren();
		const result = path.map(v => v.split(/[/\\]/).at(-1));
		const parser = new DOMParser();
		result.forEach((v, i) => {
			const listItemHTML = `
				<div class="list-item">
					<i class="fa-solid fa-grip-vertical handle"></i>
					<a>${v}</a>
					<input class="caption-xheckbox" type="checkbox" checked>
				</div>`;
				const dom = parser.parseFromString(listItemHTML, 'text/html').body.firstChild;
				dom.querySelector('.list-item a').addEventListener('click', async () => {
					await eel.openFile(path[i])();
				});
			selecetdInputList.append(dom);
		});
		selecetdInputList.value = result;
		selecetdInputCounter.textContent = `ファイル数:${path.length}`;
		if (controllerInput) {
			controllerInput.abort();
		}
		controllerInput = new AbortController();
		inputFolderLink.addEventListener('click', async () => {
			await eel.openDir(path[0].replace(/[^/\\]+$/, ''))();
		}, {signal: controllerInput.signal});
		inputFolderLink.classList.remove('btn-hidden');
	}
});

let controllerOutput;
outputBtn.addEventListener('click', async () => {
	const path = await eel.selectOutputFiles()();
	if (path) {
		outputFilePath = path;
		selectedOutputTextArea.value = path;
		if (controllerOutput) {
			controllerOutput.abort();
		}
		controllerOutput = new AbortController();
		outputFolderLink.addEventListener('click', async () => {
			await eel.openDir(path.replace(/[^/\\]+$/, ''))();
		}, {signal: controllerOutput.signal});
		outputFolderLink.classList.remove('btn-hidden');
	}
});
execBtn.addEventListener('click', async () => {
	showProgress(0);
	execBtn.classList.add('hidden-btn');
	termBtn.classList.remove('hidden-btn');
	execGuide.classList.add('guide-flash');
	execGuide.textContent = '実行中...';
	progressArea.classList.remove('progress-hidden');
	processTextArea.value = '';

	const needCaption = [];
	document.querySelectorAll('.list-item input.caption-xheckbox').forEach(i => {
		needCaption.push(i.checked);
	});
	const userSettings = {
		'inputVideo': inputFilesPath,
		'needCaption': needCaption,
		'outputVideo': outputFilePath,
		'captionMargin': document.getElementById('captionMargin').value,
		'captionSize': document.getElementById('captionSize').value,
		'captionColor': document.getElementById('captionColor').value.replace('#', '0x'),
		'captionBorderColor': document.getElementById('captionBorderColor').value.replace('#', '0x'),
		'BorderWidthRatio': document.getElementById('BorderWidthRatio').value,
		'captionDisplayTime': document.getElementById('captionDisplayTime').value,
		'captionFont': document.getElementById('captionFont').value,
		'backgroundColor': document.getElementById('backgroundColor').value.replace('#', '0x'),
		'width': document.getElementById('width').value,
		'height': document.getElementById('height').value,
		'fps': document.getElementById('fps').value,
		'sampleRate': document.getElementById('sampleRate').value,
		'preset': document.getElementById('preset').value,
		'HWEncode': document.getElementById('HWEncode').value
	}
	const settings = Object.fromEntries(
		Object.entries(userSettings).filter(([i, v]) => v !== '')
	);

	await eel.generateVideo(settings)();
});
termBtn.addEventListener('click', async () => {
	await eel.terminateProcess()();
	quitProcess('中止');
});
fontSelectBtn.addEventListener('click', async () => {
	const path = await eel.selectFontFile()();
	if (path) {
		fontSelectBtn.value = path;
	}
});
HWEncodeSelector.addEventListener('change', () => {
	if (selectedCodec !== null && HWEncodeSelector.value === 'true') {
		changePreset(selectedCodec);
	}else {
		changePreset('libx264');
	}
});
window.addEventListener('keydown', (e) => {
	if ( e.key === 'F5' || ((e.ctrlKey || e.metaKey) && e.key === 'r')) {
		e.preventDefault();
	}
	if (((e.ctrlKey || e.metaKey) && e.key === 's')) {
		e.preventDefault();
	}
	if (((e.ctrlKey || e.metaKey) && e.key === 't')) {
		e.preventDefault();
	}
	if (((e.ctrlKey || e.metaKey) && e.key === 'u')) {
		e.preventDefault();
	}
	if (((e.ctrlKey || e.metaKey) && e.key === 'T')) {
		e.preventDefault();
	}
	if (((e.ctrlKey || e.metaKey) && e.key === 'N')) {
		e.preventDefault();
	}
});
window.addEventListener('contextmenu', (e) => {
	e.preventDefault();
});


function addLog(text) {
	if (text !== undefined && typeof text === 'string') {
		processTextArea.classList.remove('font-red');
		processTextArea.value += text;
		processTextArea.scrollTop = processTextArea.scrollHeight;
	}
}
function addError(text) {
	if (text !== undefined && typeof text === 'string') {
		processTextArea.value = text;
		processTextArea.classList.add('font-red');
		processTextArea.scrollTop = processTextArea.scrollHeight;
		quitProcess('エラー');
	}
}
function showAlert(text) {
	if (text !== undefined && typeof text === 'string') {
		alert(text);
	}
}
function quitProcess(text) {
	if (text !== undefined && typeof text === 'string') {
		execBtn.classList.remove('hidden-btn');
		termBtn.classList.add('hidden-btn');
		execGuide.classList.remove('guide-flash');
		execGuide.textContent = text;
	}
}
function showProgress(progress) {
	if (progress !== undefined && !isNaN(progress)) {
		progressBar.value = Number(progress);
		progressPercentage.textContent = `${Math.trunc(Number(progress) * 100)}%`;
	}
}
function changePreset(codec) {
	if (codec !== undefined && typeof codec === 'string') {
		presetSelector.replaceChildren();
		let presets = new Map([
			['ultrafast', 'ultrafast'],
			['superfast', 'superfast'],
			['veryfast', 'veryfast'],
			['faster', 'faster'],
			['fast', 'fast'],
			['medium', 'medium'],
			['slow', ['slow', true]],
			['slower', 'slower'],
			['veryslow', 'veryslow'],
			['placebo', 'placebo']
		]);

		switch (codec) {
			case 'h264_nvenc': {
				presets = new Map([
					['p1', 'p1:fastest'],
					['p2', 'p2:faster'],
					['p3', 'p3:fast'],
					['p4', 'p4:medium'],
					['p5', ['p5:slow', true]],
					['p6', 'p6:slower'],
					['p7', 'p7:slowest']
				]);
				break;
			}
			case 'h264_qsv': {
				presets = new Map([
					['veryfast', 'veryfast'],
					['faster', 'faster'],
					['fast', 'fast'],
					['medium', 'medium'],
					['slow', ['slow', true]],
					['slower', 'slower'],
					['veryslow', 'veryslow']
				]);
				break;
			}
			case 'h264_amf': {
				presets = new Map([
					['balanced', 'balanced'],
					['speed', 'speed'],
					['quality', ['quality', true]]
				]);
				break;
			}
		}
		let optionHTML = '';
		presets.forEach((v, i) => {
			let value = v;
			let selected = '';
			if (Array.isArray(v) && v[1] === true) {
				value = v[0];
				selected = ' selected';
			}
			optionHTML += `<option value="${i}"${selected}>${value}</option>
			`;
		});
		presetSelector.insertAdjacentHTML('beforeend', optionHTML);
	}
}
function getAllLog() {
	return processTextArea.value || 'log';
}