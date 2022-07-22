import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { SSLThumbprintModalComponent } from './ssl-thumbprint-modal.component';

describe('SSLThumbprintModalComponent', () => {
    let component: SSLThumbprintModalComponent;
    let fixture: ComponentFixture<SSLThumbprintModalComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [ SSLThumbprintModalComponent ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(SSLThumbprintModalComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
