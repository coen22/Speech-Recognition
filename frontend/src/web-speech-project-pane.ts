import {customElement, property, state} from "lit/decorators.js";
import {css, html, LitElement, PropertyValues} from "lit";

@customElement("web-speech-project-pane")
export class WebSpeechProjectPane extends LitElement {

  @property() data?: {name: string, data: string}[];

  @property() selectedIdx = -1;

  //language=css
  static styles = css`
    * {
        box-sizing: border-box;
    }
      
    :host {
      display: flex;
      flex-direction: column;
      align-items: stretch;
      align-content: start;
      text-align: left;
      justify-content: flex-start;
      color: #1a2b42;
      width: 100%;
      overflow-y: auto;
    }
    
    .project {
        text-overflow: ellipsis;
        cursor: pointer;
        width: 100%;
        padding: 15px;
        -webkit-transition: all 0.1s ease;
        -moz-transition: all 0.1s ease;
        -o-transition: all 0.1s ease;
        transition: all 0.1s ease;
    }
    
    .project:hover {
        background-color: #00000011;
    }
    
    .project:active {
        background-color: #00000033;
    }
    
    .selected {
        background-color: #00000011;
    }
  `;

  render() {
    return html`
        ${this.data?.map((x: any, i) => html`
            <a @click="${() => this.projectClicked(i)}" class="project ${this.selectedIdx == i ? 'selected' : ''}">${x.name}</a>
        `)}
    `;
  }

  async projectClicked(idx: number) {
    if (this.data) {
        const event = new CustomEvent('change', {
            detail: idx
        });

        this.dispatchEvent(event);

        this.selectedIdx = idx;
    } else {
        // error
    }
  }
}