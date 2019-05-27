// https://www.freepik.com/free-vector/set-four-brick-houses_1051128.htm
// https://www.freepik.com/free-vector/disaster-concept-4-flat-icons-square-banner_3910279.htm
// https://www.freepik.com/free-vector/cars-side-front-back-icons-set_2870932.htm

const LitElement = Object.getPrototypeOf(
 customElements.get("ha-panel-lovelace")
);
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

const THEMES = {
    'two_story_garage': {
	'overlays': {
	    'garageport': { 'width': '27.8%', 'left': '73.3%', 'top': '75.91%', 'z-index': '10' },
	    'car':        { 'width': '15%', 'left': '75%', 'top': '87%', 'z-index': '20' },
	},
	
	//'weather-sun': { 'width': '20%', 'left': '85%', 'top': '15%' },
    },
};

class OverviewCard extends LitElement {

    static get properties() {
	return {
	    config: {},
	    hass: {}
	};
    }
    
    setConfig(config) {
	if (!config.house_type) {
	    throw new Error('No house type defined');
	}

	if (!THEMES[config.house_type]) {
	    throw new Error('Unsupported house type: ' + config.house_type);
	}

	this.config = config;
	this.theme = THEMES[config.house_type];
    }
    
    getCardSize() {
	return 4;
    }
    
    render() {
	return html`
            <div id="root">
	      <div id="weather">
                <img src="/local/imgs/weather-sun.png" style="width: 15%" />
              </div>
	      <div id="house">
                <img src="/local/imgs/house.png?v=0" style="width: 100%" />
                ${this._add_entities()}
	      </div>
            </div>
	    `;
    }

    _add_entities() {
	var to_add = []
	Object.keys(this.config.entities).map(ents => {
	    var entity = this.config.entities[ents];
	    var stateObj = this.hass.states[entity.entity];

	    if (stateObj) {
		if (stateObj.state == 'on') {
		    to_add.push(this._createImage(entity['type'], this.theme['overlays']));
		}
	    }
	});
        //Object.keys(this.theme['overlays']).map(overlay => this._createImage(overlay, this.theme['overlays']))
	return to_add;
    }
    
    _createImage(imageName, lookup) {


	const element = document.createElement('img');
	element.id = imageName;
	element.src = `/local/imgs/${imageName}.png?v=0`;
	element.classList.add('element');

	Object.keys(lookup[imageName]).map((prop) => {
	    element.style.setProperty(prop, lookup[imageName][prop]);
	});

	return element;
    }
    
    static get styles() {
	return css`
	    #root {
		width: 100%;
		height: auto;
		padding-top: 5%;
		padding-bottom: 5%;
	    }
            #weather {
		position: relative;
		overflow: visible;
		height: 100%;
		width: 100%;
		left: 80%;
	    }
            #house {
		position: relative;
		overflow: hidden;
		height: 100%;
		width: 90%;
		left: 5%;
		z-index: -1;
	    }
            .element {
		position: absolute;
		transform: translate(-50%, -50%);

	    }
	`;
  }
}

customElements.define('overview-card', OverviewCard);
