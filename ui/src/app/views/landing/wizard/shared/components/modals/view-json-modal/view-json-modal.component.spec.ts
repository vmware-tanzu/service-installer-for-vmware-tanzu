import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { ViewJSONModalComponent } from './view-json-modal.component';

describe('ViewJSONModalComponent', () => {
    let component: ViewJSONModalComponent;
    let fixture: ComponentFixture<ViewJSONModalComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [ ViewJSONModalComponent ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(ViewJSONModalComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
