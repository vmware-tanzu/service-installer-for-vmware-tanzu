/**
 * Angular modules
 */
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

/**
 * Third party imports
 */
import { ClarityModule } from '@clr/angular';

/**
 * App imports
 */
import { ContextualHelpComponent } from './contextual-help/contextual-help.component';
import { A11yTooltipTriggerDirective } from './directives/a11y-tooltip-trigger.directive';
import { FeatureToggleDirective } from './directives/feature-flag.directive';
import { KeyboardListenerDirective } from './directives/keyboard-listener.directive';
import { RemoveAriaLabelledByDirective } from './directives/remove-aria-labelledBy.directive';

const declaredAndExportedModules = [
    CommonModule,
    ClarityModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule
];

/**
 * Module for shared UI components
 */
@NgModule({
    imports: [
        ...declaredAndExportedModules,
    ],

    providers: [],
    exports: [
        ...declaredAndExportedModules,
        FeatureToggleDirective,
        A11yTooltipTriggerDirective,
        RemoveAriaLabelledByDirective,
        ContextualHelpComponent,
        KeyboardListenerDirective
    ],
    declarations: [
        FeatureToggleDirective,
        A11yTooltipTriggerDirective,
        RemoveAriaLabelledByDirective,
        ContextualHelpComponent,
        KeyboardListenerDirective
    ]
})
export class SharedModule { }
