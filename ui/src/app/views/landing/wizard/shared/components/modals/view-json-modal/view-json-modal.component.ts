import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { NgxJsonViewerModule } from 'ngx-json-viewer';

@Component({
    selector: 'app-view-json-modal',
    templateUrl: './view-json-modal.component.html',
    styleUrls: ['./view-json-modal.component.scss']
})
export class ViewJSONModalComponent implements OnInit {
//     @Input() thumbprint: string;
//     @Input() vcenterHost: string;
    @Input() payload;
    @Input() env;
    public inputFilename;
//     @Output() verifiedThumbprint: EventEmitter<boolean> = new EventEmitter();

    viewJson: boolean;

    constructor() {}

    ngOnInit(): void {
        this.viewJson = false;
    }

    open(filename) {
        this.inputFilename = filename;
        this.viewJson = true;
    }

    close() {
//         this.verifiedThumbprint.emit(false);
        this.viewJson = false;
    }

    continueBtnHandler() {
//         this.verifiedThumbprint.emit(true);
        this.viewJson = false;
        this.onDownload();
    }

    download(content, fileName, contentType) {
        const a = document.createElement("a");
        const file = new Blob([content], { type: contentType });
        a.href = URL.createObjectURL(file);
        a.download = fileName;
        a.click();
    }

    onDownload () {
        this.download(JSON.stringify(this.payload, null,'\t'), this.inputFilename, "json");
//         if (this.env === 'vsphere'){
//             this.download(JSON.stringify(this.payload, null,'\t'), "vsphere.json", "json");
//         } else if (this.env === 'vcf') {
//             this.download(JSON.stringify(this.payload, null,'\t'), "vcf.json", "json");
//         } else if (this.env === 'vmc') {
//             this.download(JSON.stringify(this.payload, null,'\t'), "vmc.json", "json");
//         } else if (this.env === 'vsphere-tkgs') {
//             this.download(JSON.stringify(this.payload, null,'\t'), "vsphere.json", "json");
//         }
    }

}
