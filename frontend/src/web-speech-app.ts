import { LitElement, html, css } from 'lit';
import {customElement, property, state } from 'lit/decorators.js';
import {live} from "lit/directives/live.js";
import {until} from "lit/directives/until.js";

import '@polymer/paper-progress/paper-progress';

import "@vaadin/vaadin-button/vaadin-button";

import "@vaadin/vaadin-text-field/vaadin-text-field";
import {TextFieldElement} from "@vaadin/vaadin-text-field";

import './web-speech-project-pane';
import './web-speech-detail-pane';
import {WebSpeechDetailPane} from "./web-speech-detail-pane";

import Dexie from "dexie";
import {WebSpeechProjectPane} from "./web-speech-project-pane";

export const db = new Dexie('Transcribe');

// Declare tables, IDs and indexes
db.version(2).stores({
    projects: '++id, name, data'
});

export interface TranscriptResponse {
    audio: string;
    label: string;
}

@customElement("web-speech-app")
export class WebSpeechApp extends LitElement {

  static PASSWORD = '%V66nKxF@k#=52@k';

  @property() data?: {id: number, name: string, data: string}[];

  @property() password?: string;

  @state() loading = false;

  private _projectPane?: WebSpeechProjectPane;
  private _detailPane?: WebSpeechDetailPane;

  //language=css
  static styles = css`
    * {
        box-sizing: border-box;
    }
      
    :host, main {
      max-height: 100%;
      display: flex;
      flex-direction: row;
      align-items: stretch;
      justify-content: flex-start;
      color: #1a2b42;
      text-align: center;
      width: 100%;
    }
    
    input[type="file"] {
        display: none;
    }
    
    .custom-file-upload {
        text-align: left;
        background-color: #ddd;
        display: inline-block;
        padding: 10px 15px;
        cursor: pointer;
        -webkit-transition: all 0.1s ease;
        -moz-transition: all 0.1s ease;
        -o-transition: all 0.1s ease;
        transition: all 0.1s ease;
    }
    
   .custom-file-upload:hover {
        -webkit-filter: brightness(110%);
    }
    
    .custom-file-upload:active {
        -webkit-filter: brightness(80%);
    }
    
    .side-pane, .main-content {
        display: flex;
        vertical-align: top;
        flex-direction: column;
        height: 100vh;
    }
    
    .side-pane {
        width: 250px;
        background-color: #00000005;
    }
    
    .main-content {
        width: 100%;
        overflow-y: auto;
    }
  `;

  render() {
    return html`
        <div class="main" style="display: ${this.password == WebSpeechApp.PASSWORD ? 'flex' : 'none'}; width: 100%">
            <div class="side-pane">
                ${this.loading ? html`
                    <paper-progress style="width: 100%" indeterminate></paper-progress>
                ` : html`
                    <label class="custom-file-upload">
                        <input type="file" id="myFile" name="filename" accept="audio/*" @change=${this.transcribe}/>
                        Load Audio...
                    </label>
                `}
                <label class="custom-file-upload">
                    <input type="file" id="myFile" name="filename" accept="application/json" @change=${this.load}/>
                    Load Project...
                </label>
                ${until(html`
                    <web-speech-project-pane selectedIdx="0" .data="${live(this.data)}" @change="${this.loadFromIndexed}"></web-speech-project-pane>
                `, html`
                    Loading...
                `)}
            </div>
            <div class="main-content">
                ${until(html`
                    <web-speech-detail-pane @change="${this.reloadData}" @delete="${this.loadFromIndexedAtDelete}"></web-speech-detail-pane>
                `, html`
                    Loading...
                `)}
            </div>
        </div>
    
        ${this.password == WebSpeechApp.PASSWORD ? html`
        ` : html`
            <div style="flex-direction: column; max-width: 800px; margin: auto">
            <h1>Automatic Transcription Service</h1>
            <div style="width: 100%; text-align: center">
                <vaadin-text-field
                    id="password-field"
                    label="Password"
                    ?invalid="${!!this.password && this.password != WebSpeechApp.PASSWORD}"
                    error-message="Error: wrong password"
                    @change="${this._changePassword}"></vaadin-text-field>
                
                <vaadin-button theme="primary"  @click="${this._changePassword}">Log In</vaadin-button>
            </div>
            <p style="width: 100%; text-align: center">
            To request access for this service, please contact us via 
                <a href="mailto:c.hacking@maastrichtuniversity.nl?cc=s.aarts@maastrichtuniversity.nl&subject=Transcribeer%20Tool">
                    email
                </a>.
            </p>
            <p>
                <b>DISCLAIMER: this service is part of a pilot for automatic transcription.
                All work by AWO-L is provided “AS IS”.
                Unless otherwise explicitly stated, AWO-L makes no other warranties, express or implied,
                and hereby disclaims all implied warranties, including any warranty of merchantability and warranty of
                fitness for a particular purpose.</b>
            </p>
            </div>
        `}
    `;
  }

  async _changePassword(e: CustomEvent) {
    let field = this.shadowRoot?.querySelector('#password-field') as TextFieldElement;
    this.password = field.value;

    if (this.password == WebSpeechApp.PASSWORD) {
        localStorage.removeItem('password');
        localStorage.setItem('password', this.password);
    }

    // location.reload();
  }

  async connectedCallback() {
      super.connectedCallback();
      this.password = localStorage.getItem('password') as string;

      // @ts-ignore
      this.data = await db['projects'].toArray();

      this._projectPane = this.shadowRoot?.querySelector("web-speech-project-pane") as WebSpeechProjectPane;
      this._detailPane = this.shadowRoot?.querySelector("web-speech-detail-pane") as WebSpeechDetailPane;

      if (this.data && this.data.length > 0) {
          await this.loadProject(this.data[0]);
      }
  }

  async transcribe(e: CustomEvent) {
    this.loading = true;

    let input = e.target as HTMLInputElement;

    if (input?.files?.length == 0)
        return;

    const body = new FormData();
    // @ts-ignore
    body.append("file", input?.files[0]);

    try {
        let result = await fetch("http://fhmlhsrwks0140.wired.unimaas.local:8000/transcribe/1", {
            body,
            method: "POST"
        });

        // console.log(result.ok);

        let json = await result.json();

        if (json) {
            for (let i = 0; i < json.length; i++) {
                if (json[i].label)
                    json[i].label = json[i].label?.toLocaleLowerCase();
            }
        }

        // @ts-ignore
          await db.projects.add({
            name: "New Project",
            data: json
        });

        // @ts-ignore
        this.data = await db?.projects?.toArray();
        if (this.data) {
          if (this._projectPane)
              this._projectPane.selectedIdx = this.data.length - 1;

          this.loadProject(this.data[this.data.length - 1]);
        }
    } catch (e) {
        console.error(e);
        alert("Something went wrong, maybe you've been disconnected from the VPN");
    }

    input.value = '';

    this.loading = false;
  }

  async load(e: CustomEvent) {
    let input = e.target as HTMLInputElement;

    if (input?.files?.length == 0 || input?.files == null)
        return;

    let file = input?.files[0];

    // Abuse response to read json data
    let json = await new Response(file).json() as TranscriptResponse[];

    if (json.length == 0 || !json[0].label || !json[0].audio) {
        alert("This is not a valid project file");
        return;
    }

    if (this._detailPane)
        this._detailPane.data = json;

    // Save progress
    try {
        // @ts-ignore
        let result = await db.projects.add({
            name: "Loaded Project",
            data: json
        });
    } catch (err) {
        console.log(err);
    }

    // @ts-ignore
    this.data = await db?.projects?.toArray();

    if (this.data) {
      if (this._projectPane)
          this._projectPane.selectedIdx = this.data.length - 1;

      this.loadProject(this.data[this.data.length - 1]);
    }

    input.value = '';
  }

  async loadFromIndexedAtDelete(e: CustomEvent) : Promise<void> {
      await this.reloadData();
      if (this.data && this._projectPane) {
          this.loadProject(this.data[0]);
          this._projectPane.selectedIdx = 0;
      }
  }

  loadFromIndexed(e: CustomEvent) : Promise<void> {
      return this.reloadData().then(() => {
        if (this.data)
            this.loadProject(this.data[e.detail]);
      });
  }

  loadProject(project: { id: number, name: string, data: TranscriptResponse[] | string }) {
      if (!project.data) {
          alert("An error occurred");
          return;
      }

      if (this._detailPane) {
        this._detailPane.data = undefined;

        this._detailPane.stopAudio().then(() => {
            if (this._detailPane) {
                this._detailPane.page = 0;
                this._detailPane.projectId = project.id;
                this._detailPane.projectName = project.name;

                if (typeof (project.data) == 'string')
                    this._detailPane.data = JSON.parse(project.data);
                else
                    this._detailPane.data = project.data;
            }
        })
      }
  }

  async reloadData() {
      // TODO optimise
      // @ts-ignore
      this.data = await db?.projects?.toArray();
  }
}