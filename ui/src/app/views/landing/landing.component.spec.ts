// Angular modules
import { TestBed, waitForAsync } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

// App imports
import { LandingComponent } from './landing.component';

describe('LandingComponent', () => {
    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            imports: [
                RouterTestingModule
            ],
            declarations: [
                LandingComponent
            ]
        }).compileComponents();
    }));

    it('should exist', () => {
        const fixture = TestBed.createComponent(LandingComponent);
        const landingComponent = fixture.debugElement.componentInstance;
        expect(landingComponent).toBeTruthy();
    });
});
