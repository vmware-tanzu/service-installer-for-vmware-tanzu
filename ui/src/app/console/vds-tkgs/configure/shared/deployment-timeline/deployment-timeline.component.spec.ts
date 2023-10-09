import { ComponentFixture, TestBed } from '@angular/core/testing';
import { APIClient } from 'src/app/swagger/api-client.service';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { DeploymentTimelineComponent } from './deployment-timeline.component';

describe('DeploymentTimelineComponent', () => {
  let component: DeploymentTimelineComponent;
  let fixture: ComponentFixture<DeploymentTimelineComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        APIClient
    ],
    schemas: [
        CUSTOM_ELEMENTS_SCHEMA
    ],
      declarations: [ DeploymentTimelineComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeploymentTimelineComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
