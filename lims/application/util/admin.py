from django import forms
from django.contrib import admin, messages
from django.db import transaction, connection, OperationalError
from django.apps import apps
from sample.models import Sample, SampleTestMap
from accessioning.models import Accession


class TZIndependentAdmin(admin.ModelAdmin):
    tz_independent_fields = []

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in self.tz_independent_fields:
            kwargs['widget'] = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def create_display_method(self, column_name):
        def display_method(obj):
            tz_name = getattr(obj, f"{column_name}_timezone", None)
            if tz_name and getattr(obj, column_name, None):
                return f"{getattr(obj, column_name)} ({tz_name})"
            return getattr(obj, column_name)

        display_method.short_description = f"{column_name.replace('_', ' ').title()} (TZ Independent)"
        return display_method

    def return_tz_independent_column_values(self):
        list_display_as_list = []
        for column in self.tz_independent_fields:
            display_method = self.create_display_method(column)
            method_name = f"{column}_display"
            setattr(self, method_name, display_method)
            list_display_as_list.append(method_name)

        return list_display_as_list


class GulfModelAdmin(admin.ModelAdmin):
    def get_inherited_tables(self, model):
        # Recursively getting all tables inherited from the given model.
        tables = [model._meta.db_table]

        parent_model = model
        while hasattr(parent_model, '_meta') and parent_model._meta.parents:
            parent_model = list(parent_model._meta.parents.keys())[0]  # Get the first parent
            tables.append(parent_model._meta.db_table)

        return tables

    def custom_generic_delete(self, request, primary_keys, model):
        if "Sample" == model.__name__:
            non_initial_samples = Sample.objects.filter(sample_id__in=primary_keys).exclude(sample_status="Initial")
            if non_initial_samples.exists():
                sample_ids = ", ".join(non_initial_samples.values_list('sample_id', flat=True))
                self.message_user(request, f"Cannot delete samples with status other than 'Initial': {sample_ids}",
                                  level=messages.ERROR)
                return

            if SampleTestMap.objects.filter(sample_id__in=primary_keys).exists():
                SampleTestMap.objects.filter(sample_id__in=primary_keys).delete()

        if "Accession" == model.__name__:
            accessions = Accession.objects.filter(accession_id__in=primary_keys)
            accessions_with_samples = []
            for accession in accessions:
                if Sample.objects.filter(accession_id=accession.accession_id).exists():
                    accessions_with_samples.append(accession.accession_id)

            if accessions_with_samples:
                accession_ids = ", ".join(accessions_with_samples)
                self.message_user(request, f"Cannot delete accession(s) with associated sample(s): {accession_ids}",
                                  level=messages.ERROR)
                return
        pk_list_str = ", ".join([f"'{pk}'" for pk in primary_keys])
        inherited_tables = self.get_inherited_tables(model)

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    for table in inherited_tables:
                        try:
                            # Dynamically retrieving the model based on the table name
                            app_label, model_name = table.split('_', 1)  # Spliting app label and model name
                            current_model = apps.get_model(app_label, model_name)
                            pk_field = self.get_pk_field_for_table(current_model, table)  # Using current_model

                            delete_query = f"DELETE FROM {table} WHERE {pk_field} IN ({pk_list_str})"
                            cursor.execute(delete_query)
                        except OperationalError as e:
                            self.message_user(request, f"Error deleting from {table}: {str(e)}. Standard delete used.",
                                              messages.WARNING)
                            raise  # Rollback transaction.
            self.message_user(request, "Selected records deleted successfully!", messages.SUCCESS)

        except Exception as e:
            super().delete_queryset(request, self.get_queryset(request).filter(
                pk__in=primary_keys))  # Fallback to standard delete.

    def get_pk_field_for_table(self, model, table_name):
        # Determining the primary key field for a given table.

        if model._meta.db_table == table_name:
            # Checking if it's a child model with multi-table inheritance
            for field in model._meta.fields:
                if field.one_to_one and field.remote_field and field.remote_field.model in model._meta.parents:
                    # Checking if the field name ends with '_id'
                    if field.name.endswith('_id'):
                        return field.name  # Returning the field name as is
                    else:
                        return field.name + '_id'  # Adding _id suffix
            # If not a child model, return the model's actual primary key field name
            return model._meta.pk.name

        # Finding the parent model that has a ForeignKey to the current model
        parent_model = None
        for parent in model._meta.parents:
            if parent._meta.db_table == table_name:
                parent_model = parent
                break

        if parent_model:
            # Finding the ForeignKey field pointing to the parent model
            for field in model._meta.fields:
                if field.remote_field and field.remote_field.model == parent_model:
                    return field.name

        return model._meta.pk.name  # Fallback to the model's actual primary key

    @admin.action(description="Delete selected record(s)")
    def delete_custom(self, request, queryset):
        primary_keys = [str(obj.pk) for obj in queryset]
        model = queryset.model
        self.custom_generic_delete(request, primary_keys, model)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    actions = [delete_custom]
