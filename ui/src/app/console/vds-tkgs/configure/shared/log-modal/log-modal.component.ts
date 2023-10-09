import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-log-modal',
  templateUrl: './log-modal.component.html',
  styleUrls: ['./log-modal.component.scss']
})
export class LogModalComponent implements OnInit {
  viewStreamingLogs: Boolean;
  startStreamingLogs: Boolean;

  constructor() { }

  ngOnInit(): void {
    this.viewStreamingLogs = true;
  }

  openLogModal() {
    this.viewStreamingLogs = true;
    this.startStreamingLogs = true;
  }

  close() {
    this.startStreamingLogs = false;
  }

}
