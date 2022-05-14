// Angular imports
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { TestBed, waitForAsync } from '@angular/core/testing';
import { HttpClientModule } from '@angular/common/http';
import { RouterTestingModule } from '@angular/router/testing';


// App imports
import { AppComponent } from './app.component';
// import { ThemeToggleComponent } from './shared/components/theme-toggle/theme-toggle.component';
// import { APIClient } from './swagger/api-client.service';
// import { BrandingService } from './shared/service/branding.service';
// import { BrandingServiceStub } from './testing/branding.service.stub';

describe('AppComponent', () => {
    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
            declarations: [
                AppComponent,
            ],
            imports: [
                HttpClientModule,
                RouterTestingModule,
            ],
            schemas: [
                CUSTOM_ELEMENTS_SCHEMA,
            ]
        }).compileComponents();
    }));
    
    it('should create the app', () => {
        const fixture = TestBed.createComponent(AppComponent);
        const app = fixture.debugElement.componentInstance;
        expect(app).toBeTruthy();
    });
});
