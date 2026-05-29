<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StoreAnalyticsRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     */
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Get the validation rules that apply to the request.
     *
     * @return array<string, \Illuminate\Contracts\Validation\ValidationRule|array|string>
     */
    public function rules(): array
    {
        return [
            'people_count' => 'required|integer|min:0|max:10000',
            'queue_length' => 'required|integer|min:0|max:10000',
            'entry_count' => 'required|integer|min:0|max:100000',
            'exit_count' => 'required|integer|min:0|max:100000',
        ];
    }

    /**
     * Get custom messages for validator errors.
     *
     * @return array<string, string>
     */
    public function messages(): array
    {
        return [
            'people_count.required' => 'People count is required',
            'people_count.integer' => 'People count must be an integer',
            'people_count.min' => 'People count cannot be negative',
            'queue_length.required' => 'Queue length is required',
            'queue_length.integer' => 'Queue length must be an integer',
            'entry_count.required' => 'Entry count is required',
            'entry_count.integer' => 'Entry count must be an integer',
            'exit_count.required' => 'Exit count is required',
            'exit_count.integer' => 'Exit count must be an integer',
        ];
    }
}
