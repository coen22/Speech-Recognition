import {customElement, property, state} from "lit/decorators.js";
import {css, html, LitElement} from "lit";
import {repeat} from "lit/directives/repeat.js";
import {until} from "lit/directives/until.js";

import {TranscriptResponse, WebSpeechApp} from "./web-speech-app";
import { db } from './web-speech-app';

import "@vaadin/vaadin-checkbox/vaadin-checkbox";
import {CheckboxElement} from "@vaadin/vaadin-checkbox";

import "@vaadin/vaadin-text-field/vaadin-text-area";
import {TextAreaElement} from "@vaadin/vaadin-text-field/vaadin-text-area";
import {TextFieldElement} from "@vaadin/vaadin-text-field";
import {Table} from "dexie";

const playIcon = new URL('../../assets/play.svg', import.meta.url).href;
const stopIcon = new URL('../../assets/stop.svg', import.meta.url).href;

const playSymbol = "▶";
const stopSymbol = "◾";

@customElement("web-speech-detail-pane")
export class WebSpeechDetailPane extends LitElement {

  private static instance: WebSpeechDetailPane;

  private static PAGE_SIZE = 20;

  private static SAVE_TIMEOUT = 1000;

  @property() projectId = -1;

  @property() projectName?: string;

  @property() data?: TranscriptResponse[];

  @state() page = 0;

  @state() audio?: HTMLAudioElement;
  @state() playingIndex?: number;

  private saveNameTimeout?: number;
  private saveDataTimeout?: number;

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
      padding: 30px;
      max-width: 1000px;
      margin: 0 auto;
    }
    
    vaadin-button {
        cursor: pointer;
    }
    
    .download {
        background-color: limegreen;
    }
    
    .pages {
        text-align: center;
    }
    
    .page {
        padding: 7px 11px;
        cursor: pointer;
    }
    
    .selected-page {
        background-color: black;
        color: white;
        border-radius: 5px;
    }
    
    .play-button {
        width: 23px;
        vertical-align: center;
        text-align: center;
    }
  `;

  render() {
    return until(html`
        ${this.data && this.data.length > 0 ? html`
            <vaadin-text-field
                id="project-name-field"
                label="Project Name"
                @input="${this._updateName}"
                value="${this.projectName}"></vaadin-text-field>
            <table>
                ${repeat(this.data.slice(this.page * WebSpeechDetailPane.PAGE_SIZE, (this.page + 1) * WebSpeechDetailPane.PAGE_SIZE), (transcript, idx) => html`
                    <tr>
                        <td class="play-button">
                            <a style="cursor: pointer; height: 100%" @click="${async () => await this.stopOrPlayAudio(idx + this.page * WebSpeechDetailPane.PAGE_SIZE)}">
                                ${this.playingIndex == idx + this.page * WebSpeechDetailPane.PAGE_SIZE ? stopSymbol : playSymbol}
                            </a>
                        </td>
                        <td style="text-align: left; width: *">
                            <vaadin-text-area style="width: 100%" 
                                              value="${transcript.label}"
                                              @input="${(e: CustomEvent) => this._updateData(e, idx + this.page * WebSpeechDetailPane.PAGE_SIZE)}"></vaadin-text-area>
                        </td>
                    </tr>
                `)}
            </table>
            ${this.data.length > WebSpeechDetailPane.PAGE_SIZE ? html`
                <p class="pages">
                    ${repeat(this.range(0, Math.floor(this.data.length / WebSpeechDetailPane.PAGE_SIZE) + 2), (num) => html`
                        <a class="page ${num == this.page ? 'selected-page' : ''}" @click="${async () => {
                            this.page = num;
                            await this.stopAudio();
                        }}">${num + 1}</a>
                    `)}
                </p>
            ` : ''}
            <div style="width: 100%; display: flex; flex-direction: row; justify-content: space-between; margin: 10px 0">
                <vaadin-button theme="error primary"  @click="${this._removeProject}">Remove Project</vaadin-button>
                <span style="flex-grow: 1"></span>
                <vaadin-button theme="success"  @click="${this._downloadProject}">Download Project (.json)</vaadin-button>
                <span>&nbsp;</span>
                <vaadin-button theme="success"  @click="${this._downloadTranscript}">Download Transcript (.docx)</vaadin-button>
                <span>&nbsp;</span>
                <vaadin-button theme="primary"  @click="${this._sendForTraining}">Use for Training</vaadin-button>
            </div>
            <div style="width: 100%; display: flex; flex-direction: row; justify-content: space-between; margin: 10px 0">
                <span style="flex-grow: 1"></span>
                <vaadin-checkbox id="line-breaks" ?checked="${true}" checked>Use Line Breaks</vaadin-checkbox>
            </div>
        ` : html`
            No project selected
        `}
    `, html`
        Loading...
    `);
  }

  connectedCallback() {
      super.connectedCallback();

      WebSpeechDetailPane.instance = this;

      try {
          let data = localStorage.getItem('data') as string;
          if (data)
            this.data = JSON.parse(data);
      } catch (err) {
          // This code runs if there were any errors.
          console.log(err);
      }
  }

  _updateName(e: CustomEvent, idx: number) : void {
    let field = e.target as TextFieldElement;

    this.projectName = field.value;

    if (this.projectId >= 0) {
        window.clearTimeout(this.saveNameTimeout);
        this.saveNameTimeout = window.setTimeout(this.saveName, WebSpeechDetailPane.SAVE_TIMEOUT);
    }
  }

  private saveName() {
    // @ts-ignore
    db.projects.update(WebSpeechDetailPane.instance.projectId, {
        "name": WebSpeechDetailPane.instance.projectName
    });

    const event = new CustomEvent('change', {
        detail: WebSpeechDetailPane.instance.projectId
    });

    WebSpeechDetailPane.instance.dispatchEvent(event);
  }

  _updateData(e: CustomEvent, idx: number) : void {
    let area = e.target as TextAreaElement;

    if (this.data) {
        this.data[idx].label = area.value;

        if (this.projectId >= 0) {
            window.clearTimeout(this.saveDataTimeout);
            this.saveDataTimeout = window.setTimeout(this.saveData, WebSpeechDetailPane.SAVE_TIMEOUT);
        }
    } else {
        console.log("Error: no data");
    }
  }

  private saveData() {
    // @ts-ignore
    db.projects.update(WebSpeechDetailPane.instance.projectId, {
        "data": WebSpeechDetailPane.instance.data
    });
  }

  async _sendForTraining(e: CustomEvent) {
    if (confirm("Are you sure that you want to send this information to the server for improving the speech recognition?")) {
      const body = new FormData();

      // @ts-ignore
      body.append("file_data", JSON.stringify(this.data));

      let result = await fetch("http://fhmlhsrwks0140.wired.unimaas.local:8000/save_data", {
        body,
        method: "POST"
      });
    }
  }

  _downloadProject(e: CustomEvent) {
    let data = "data:application/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.data));
    let a = document.createElement('a');
    a.href = data;
    a.download = "project.json";
    a.click();
  }

  _downloadTranscript() {
    let useLineBreaks = true;

    let checkbox = this.shadowRoot?.getElementById("line-breaks") as CheckboxElement;
    if (checkbox)
        useLineBreaks = checkbox.checked;

    console.log(this.createHTMLDoc(useLineBreaks));

    let data = "data:text/html;charset=utf-8," + encodeURIComponent(this.createHTMLDoc(useLineBreaks));
    let a = document.createElement('a');
    a.href = data;
    a.download = "project.html";
    a.click();
  }

  private createHTMLDoc(withBreaks = true) : string {
    let out = `
        <head>
          <meta charset="UTF-8">
        </head>
    `;

    if (withBreaks) {
        this.data?.forEach(el => {
            if (el.label)
                out += `<p>${el.label.replace(/ /g, '&nbsp;')}</p>`;
        });
    } else {
        return "" + this.data?.map(el => el.label).join(' ').replace(/ /g, '&nbsp;');
    }

    return out;
  }

  async stopOrPlayAudio(idx: number) {
      if (this.playingIndex == idx) {
          await this.stopAudio();
      } else {
          await this.playAudio(idx);
      }
  }

  async playAudio(idx: number) {
      try {
        await this.stopAudio();

        if (this.data) {
            let base64string = this.data[idx].audio;
            this.audio = new Audio("data:audio/wav;base64," + base64string);

            this.playingIndex = idx;
            this.requestUpdate();

            this.audio.onended = () => {
                if (this.playingIndex == idx)
                    this.playingIndex = undefined;

                this.requestUpdate();
            };

            this.audio.onpause = () => {
                if (this.playingIndex == idx)
                    this.playingIndex = undefined;

                this.requestUpdate();
            };

            await this.audio.play();
        }
      } catch (e) {
        console.error(e);
      }
  }

  public async stopAudio() {
    if (this.audio) {
        this.audio.pause();
        this.audio.currentTime = 0;
        this.requestUpdate();
    }
  }

  _removeProject() {
    if (confirm(`Are you sure you want to remove project '${this.projectName}'?`)) {
        // @ts-ignore
        let projects = db.projects as Table;
        projects.delete(this.projectId);

        const event = new CustomEvent('delete', {
            detail: this.projectId
        });

        // this.projectId = -1;
        // this.projectName = undefined;
        // this.data = undefined;

        this.dispatchEvent(event);
    }
  }

  range(start: number, end: number) {
      return Array.apply(0, Array(end - 1))
        .map((element, index) => index + start);
  }
}