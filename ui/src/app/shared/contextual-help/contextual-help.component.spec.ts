/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { ContextualHelpComponent } from './contextual-help.component';
import mockIndex from '../../../contextualHelpDocs/mockIndex.json';

declare let elasticlunr: any;

describe('ContextualHelpComponent', () => {
    let component: ContextualHelpComponent;
    let fixture: ComponentFixture<ContextualHelpComponent>;

    beforeEach(waitForAsync(() => {
        TestBed.configureTestingModule({
        declarations: [ ContextualHelpComponent ]
        })
        .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(ContextualHelpComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        component.lunrIndex = elasticlunr.Index.load(mockIndex);
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should show contextual help component', () => {
        component.show(['step1']);
        expect(component.visible).toBeTrue();
        expect(component.htmlContentIndexArray.length).toEqual(1);
    });

    it('should hide contextual help component', () => {
        component.hide();
        expect(component.visible).toBeFalse();
    });

    it('should show detail for a topic', () => {
        const mockData = {
            htmlContent: '<p>hello world</p>',
            tags: ['step1'],
            title: 'docker step 1'
        };
        component.showContent(mockData);
        expect(component.isTopicView).toBeFalse();
        expect(component.htmlContentIndex).toEqual(mockData);
    });

    it('should navigate back to topic', () => {
        component.navigateBack();
        expect(component.isTopicView).toBeTrue();
    });

    it('should toggle pin', () => {
        component.togglePin();
        expect(component.isPinned).toBeTrue();
        component.togglePin();
        expect(component.isPinned).toBeFalse();
    })
});
